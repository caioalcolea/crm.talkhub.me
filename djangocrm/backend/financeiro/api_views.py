import datetime
import logging
import uuid as uuid_mod
from decimal import Decimal

from django.db import transaction
from django.db.models import Case, Count, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from accounts.models import Account
from common.permissions import HasOrgContext
from contacts.models import Contact
from financeiro.constants import FINANCEIRO_CURRENCY_CODES, FINANCEIRO_CURRENCY_SYMBOLS
from financeiro.exchange_rates import ExchangeRateError, get_exchange_rate
from financeiro.models import (
    FormaPagamento,
    Lancamento,
    Parcela,
    PaymentTransaction,
    PlanoDeContas,
    PlanoDeContasGrupo,
)
from financeiro.permissions import HasFinancialAccess
from financeiro.serializers import (
    FormaPagamentoSerializer,
    LancamentoCreateSerializer,
    LancamentoDetailSerializer,
    LancamentoFullUpdateSerializer,
    LancamentoListSerializer,
    LancamentoUpdateSerializer,
    ParcelaBulkPaySerializer,
    ParcelaPaySerializer,
    ParcelaSerializer,
    PaymentTransactionCreateSerializer,
    PaymentTransactionDetailSerializer,
    PaymentTransactionListSerializer,
    PixGenerateSerializer,
    PlanoDeContasGrupoSerializer,
    PlanoDeContasGrupoTreeSerializer,
    PlanoDeContasSerializer,
)
from invoices.models import Invoice
from opportunity.models import Opportunity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _parse_int_param(params, name, default):
    """Parse integer query param with safe fallback."""
    try:
        return int(params.get(name, default))
    except (TypeError, ValueError):
        return default


def _valid_uuid(value):
    """Return a valid UUID or None."""
    if not value:
        return None
    try:
        return uuid_mod.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _parse_date(value):
    """Parse ISO date string, return None on invalid."""
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _d(val):
    """Decimal → float for JSON serialisation."""
    return float(val) if val else 0.0


class FinanceiroMixin:
    """Common mixin for all financeiro viewsets."""

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get_org(self):
        return self.request.profile.org

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(org=self.get_org())

    def perform_create(self, serializer):
        serializer.save(org=self.get_org())


# =============================================================================
# Plano de Contas
# =============================================================================


class PlanoDeContasGrupoViewSet(FinanceiroMixin, ModelViewSet):
    queryset = PlanoDeContasGrupo.objects.all()
    serializer_class = PlanoDeContasGrupoSerializer

    def get_serializer_class(self):
        if self.action == "list" and self.request.query_params.get("tree") == "true":
            return PlanoDeContasGrupoTreeSerializer
        return PlanoDeContasGrupoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("active_only") == "true":
            qs = qs.filter(is_active=True)
        return qs.prefetch_related("contas")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system_default:
            return Response(
                {"detail": "Grupos padrão do sistema não podem ser deletados. Use arquivar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Lancamento.objects.filter(plano_de_contas__grupo=instance).exists():
            return Response(
                {"detail": "Este grupo possui lançamentos vinculados. Arquive em vez de deletar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class PlanoDeContasViewSet(FinanceiroMixin, ModelViewSet):
    queryset = PlanoDeContas.objects.select_related("grupo").all()
    serializer_class = PlanoDeContasSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        grupo_id = self.request.query_params.get("grupo")
        if grupo_id:
            qs = qs.filter(grupo_id=grupo_id)
        if self.request.query_params.get("active_only") == "true":
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system_default:
            return Response(
                {"detail": "Contas padrão do sistema não podem ser deletadas. Use arquivar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Lancamento.objects.filter(plano_de_contas=instance).exists():
            return Response(
                {"detail": "Esta conta possui lançamentos vinculados. Arquive em vez de deletar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


# =============================================================================
# Forma de Pagamento
# =============================================================================


class FormaPagamentoViewSet(FinanceiroMixin, ModelViewSet):
    queryset = FormaPagamento.objects.all()
    serializer_class = FormaPagamentoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("active_only") == "true":
            qs = qs.filter(is_active=True)
        return qs


# =============================================================================
# Lancamento
# =============================================================================


class LancamentoViewSet(FinanceiroMixin, ModelViewSet):
    queryset = Lancamento.objects.select_related(
        "plano_de_contas",
        "plano_de_contas__grupo",
        "account",
        "contact",
        "opportunity",
        "invoice",
        "forma_pagamento",
    ).prefetch_related("parcelas")

    def get_object(self):
        # Cache the object to avoid repeated DB hits (get_serializer_class + view).
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object()
        return self._cached_object

    def get_serializer_class(self):
        if self.action == "create":
            return LancamentoCreateSerializer
        if self.action in ("update", "partial_update"):
            obj = self.get_object()
            has_paid = obj.parcelas.filter(status="PAGO").exists()
            if not has_paid and obj.status != "CANCELADO":
                return LancamentoFullUpdateSerializer
            return LancamentoUpdateSerializer
        if self.action == "retrieve":
            return LancamentoDetailSerializer
        return LancamentoListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        tipo = params.get("tipo")
        if tipo in ("RECEBER", "PAGAR"):
            qs = qs.filter(tipo=tipo)

        status_filter = params.get("status")
        if status_filter in ("ABERTO", "PAGO", "CANCELADO"):
            qs = qs.filter(status=status_filter)

        plano = _valid_uuid(params.get("plano_de_contas"))
        if plano:
            qs = qs.filter(plano_de_contas_id=plano)

        account = _valid_uuid(params.get("account"))
        if account:
            qs = qs.filter(account_id=account)

        contact = _valid_uuid(params.get("contact"))
        if contact:
            qs = qs.filter(contact_id=contact)

        search = params.get("search")
        if search:
            qs = qs.filter(descricao__icontains=search)

        date_from = _parse_date(params.get("date_from"))
        if date_from:
            qs = qs.filter(data_primeiro_vencimento__gte=date_from)

        date_to = _parse_date(params.get("date_to"))
        if date_to:
            qs = qs.filter(data_primeiro_vencimento__lte=date_to)

        return qs

    def _fetch_exchange_rate(self, currency, org, date):
        """Fetch exchange rate, raising DRF ValidationError on failure."""
        if currency == org.default_currency:
            return Decimal("1")
        try:
            return get_exchange_rate(currency, org.default_currency, date)
        except ExchangeRateError as e:
            raise DRFValidationError({"exchange_rate_to_base": str(e)})

    def perform_create(self, serializer):
        org = self.get_org()
        data = serializer.validated_data

        extra = {}
        if data.get("exchange_rate_type") == "VARIAVEL":
            extra["exchange_rate_to_base"] = self._fetch_exchange_rate(
                data.get("currency", "BRL"), org, data.get("data_primeiro_vencimento"),
            )

        lancamento = serializer.save(org=org, **extra)
        lancamento.generate_parcelas()

    def perform_update(self, serializer):
        instance = serializer.instance
        data = serializer.validated_data

        financial_fields = {
            "valor_total", "numero_parcelas", "data_primeiro_vencimento",
            "currency", "exchange_rate_to_base", "exchange_rate_type",
            "is_recorrente", "recorrencia_tipo",
        }
        financials_changed = bool(financial_fields & set(data.keys()))

        if data.get("exchange_rate_type") == "VARIAVEL":
            currency = data.get("currency", instance.currency)
            data["exchange_rate_to_base"] = self._fetch_exchange_rate(
                currency, self.get_org(),
                data.get("data_primeiro_vencimento", instance.data_primeiro_vencimento),
            )

        instance = serializer.save()

        if financials_changed and not instance.parcelas.filter(status="PAGO").exists():
            with transaction.atomic():
                instance.parcelas.all().delete()
                instance.generate_parcelas()
                instance.update_status()

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        lancamento = self.get_object()
        if lancamento.status == "CANCELADO":
            return Response(
                {"detail": "Lançamento já está cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            lancamento.parcelas.filter(status="ABERTO").update(status="CANCELADO")
            lancamento.update_status()
        lancamento.refresh_from_db()
        return Response(
            LancamentoDetailSerializer(lancamento).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get"])
    def parcelas(self, request, pk=None):
        lancamento = self.get_object()
        parcelas = lancamento.parcelas.all()
        serializer = ParcelaSerializer(parcelas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def reminders(self, request, pk=None):
        """List or create reminder policies for this lancamento."""
        from django.contrib.contenttypes.models import ContentType
        from assistant.models import ReminderPolicy, ScheduledJob
        from assistant.serializers import (
            ReminderPolicySerializer,
            ReminderPolicyWriteSerializer,
            ScheduledJobSerializer,
        )
        from assistant.tasks import recalculate_policy_schedules

        lancamento = self.get_object()
        ct = ContentType.objects.get_for_model(Lancamento)

        if request.method == "GET":
            policies = ReminderPolicy.objects.filter(
                org=request.profile.org,
                target_content_type=ct,
                target_object_id=lancamento.id,
            ).order_by("-created_at")

            source_ct = ContentType.objects.get_for_model(ReminderPolicy)
            data = ReminderPolicySerializer(policies, many=True).data
            for item in data:
                jobs = ScheduledJob.objects.filter(
                    source_content_type=source_ct,
                    source_object_id=item["id"],
                    status__in=["pending", "locked"],
                ).order_by("due_at")[:10]
                item["upcoming_jobs"] = ScheduledJobSerializer(jobs, many=True).data
            return Response(data)

        # POST — create a new policy for this lancamento
        serializer = ReminderPolicyWriteSerializer(
            data={
                **request.data,
                "target_type": "financeiro.lancamento",
                "target_object_id": str(lancamento.id),
                "module_key": "financeiro",
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()
        recalculate_policy_schedules.delay(str(policy.id))
        return Response(
            ReminderPolicySerializer(policy).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Parcela
# =============================================================================


class ParcelaViewSet(FinanceiroMixin, ModelViewSet):
    queryset = Parcela.objects.select_related(
        "lancamento",
        "lancamento__account",
        "lancamento__contact",
        "lancamento__plano_de_contas",
    )
    serializer_class = ParcelaSerializer
    # "post" is required for @action endpoints (pay, cancel, bulk-pay).
    # Direct create via POST to the list URL is disabled by overriding create().
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        tipo = params.get("tipo")
        if tipo in ("RECEBER", "PAGAR"):
            qs = qs.filter(lancamento__tipo=tipo)

        status_filter = params.get("status")
        if status_filter == "all":
            pass  # Show everything including CANCELADO
        elif status_filter in ("ABERTO", "PAGO", "CANCELADO"):
            qs = qs.filter(status=status_filter)
        else:
            qs = qs.exclude(status="CANCELADO")

        account = _valid_uuid(params.get("account"))
        if account:
            qs = qs.filter(lancamento__account_id=account)

        contact = _valid_uuid(params.get("contact"))
        if contact:
            qs = qs.filter(lancamento__contact_id=contact)

        plano = _valid_uuid(params.get("plano_de_contas"))
        if plano:
            qs = qs.filter(lancamento__plano_de_contas_id=plano)

        venc_from = _parse_date(params.get("vencimento_from"))
        if venc_from:
            qs = qs.filter(data_vencimento__gte=venc_from)

        venc_to = _parse_date(params.get("vencimento_to"))
        if venc_to:
            qs = qs.filter(data_vencimento__lte=venc_to)

        search = params.get("search")
        if search:
            qs = qs.filter(lancamento__descricao__icontains=search)

        ordering = params.get("ordering", "data_vencimento")
        allowed_ordering = {
            "data_vencimento", "-data_vencimento",
            "valor_parcela", "-valor_parcela", "status",
        }
        if ordering in allowed_ordering:
            qs = qs.order_by(ordering)

        return qs

    def create(self, request, *args, **kwargs):
        """Parcelas are created automatically by LancamentoViewSet. Block direct creation."""
        raise MethodNotAllowed("POST")

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        parcela = self.get_object()
        if parcela.status != "ABERTO":
            return Response(
                {"detail": "Parcela não está aberta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if parcela.lancamento.status == "CANCELADO":
            return Response(
                {"detail": "Não é possível pagar parcela de lançamento cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = ParcelaPaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            parcela.data_pagamento = ser.validated_data.get(
                "data_pagamento", datetime.date.today()
            )
            parcela.save()
            parcela.lancamento.update_status()

        return Response(ParcelaSerializer(parcela).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        parcela = self.get_object()
        if parcela.status == "PAGO":
            return Response(
                {"detail": "Não é possível cancelar parcela já paga."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if parcela.status == "CANCELADO":
            return Response(
                {"detail": "Parcela já está cancelada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            parcela.status = "CANCELADO"
            parcela.save()
            parcela.lancamento.update_status()
        return Response(ParcelaSerializer(parcela).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="bulk-pay")
    def bulk_pay(self, request):
        ser = ParcelaBulkPaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        data_pagamento = ser.validated_data.get(
            "data_pagamento", datetime.date.today()
        )
        parcela_ids = ser.validated_data["parcela_ids"]

        with transaction.atomic():
            parcelas = list(
                self.get_queryset()
                .filter(id__in=parcela_ids, status="ABERTO")
                .select_for_update()
            )

            updated_lancamentos = set()
            for parcela in parcelas:
                parcela.data_pagamento = data_pagamento
                parcela.save()
                updated_lancamentos.add(parcela.lancamento_id)

            for lanc in Lancamento.objects.filter(id__in=updated_lancamentos):
                lanc.update_status()

        return Response(
            {"detail": f"{len(parcelas)} parcelas marcadas como pagas."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Reports
# =============================================================================


class DashboardReportView(APIView):
    """Dashboard KPIs, monthly cash flow, next due date, and recent transactions."""

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_kpis(self, parcelas_ano, parcelas_org, today):
        """Compute main KPIs using conditional aggregation (single query per scope)."""
        _SUM = lambda flt: Coalesce(  # noqa: E731
            Sum("valor_parcela_convertido", filter=flt), Decimal("0")
        )

        year_agg = parcelas_ano.aggregate(
            total_receber=_SUM(Q(lancamento__tipo="RECEBER", status="ABERTO")),
            total_pagar=_SUM(Q(lancamento__tipo="PAGAR", status="ABERTO")),
            total_abertas=Count("id", filter=Q(status="ABERTO")),
        )

        month_agg = parcelas_org.filter(
            data_pagamento__year=today.year, data_pagamento__month=today.month, status="PAGO",
        ).aggregate(
            recebido_no_mes=_SUM(Q(lancamento__tipo="RECEBER")),
            pago_no_mes=_SUM(Q(lancamento__tipo="PAGAR")),
        )

        overdue_agg = parcelas_org.filter(
            status="ABERTO", data_vencimento__lt=today,
        ).aggregate(
            total_vencido=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")),
            total_vencidas_count=Count("id"),
        )

        total_abertas = year_agg["total_abertas"]
        total_vencidas_count = overdue_agg["total_vencidas_count"]
        pct_vencidas = (
            round((total_vencidas_count / total_abertas) * 100, 1)
            if total_abertas > 0 else 0
        )

        recebido = month_agg["recebido_no_mes"]
        pago = month_agg["pago_no_mes"]

        return {
            "total_receber": year_agg["total_receber"],
            "total_pagar": year_agg["total_pagar"],
            "recebido_no_mes": recebido,
            "pago_no_mes": pago,
            "total_vencido": overdue_agg["total_vencido"],
            "pct_vencidas": pct_vencidas,
            "saldo": recebido - pago,
        }

    def _get_saldo_projetado(self, parcelas_org, ano, today):
        """Saldo projetado: ALL (PAGO+ABERTO) RECEBER - PAGAR, excludes CANCELADO."""
        _SUM = lambda flt: Coalesce(  # noqa: E731
            Sum("valor_parcela_convertido", filter=flt), Decimal("0")
        )

        mes_agg = parcelas_org.filter(
            competencia_ano=today.year, competencia_mes=today.month,
        ).exclude(status="CANCELADO").aggregate(
            receber=_SUM(Q(lancamento__tipo="RECEBER")),
            pagar=_SUM(Q(lancamento__tipo="PAGAR")),
        )

        ano_agg = parcelas_org.filter(
            competencia_ano=ano,
        ).exclude(status="CANCELADO").aggregate(
            receber=_SUM(Q(lancamento__tipo="RECEBER")),
            pagar=_SUM(Q(lancamento__tipo="PAGAR")),
        )

        saldo_mes = mes_agg["receber"] - mes_agg["pagar"]
        saldo_ano = ano_agg["receber"] - ano_agg["pagar"]
        return {"saldo_projetado_mes": saldo_mes, "saldo_projetado_ano": saldo_ano}

    def _get_fluxo_mensal(self, parcelas_org, ano):
        """Monthly cash flow built from a single annotated query."""
        fluxo_qs = (
            parcelas_org.filter(competencia_ano=ano)
            .exclude(status="CANCELADO")
            .values("lancamento__tipo", "competencia_mes", "status")
            .annotate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))
        )
        lookup = {}
        for row in fluxo_qs:
            key = (row["lancamento__tipo"], row["competencia_mes"], row["status"])
            lookup[key] = _d(row["total"])

        fluxo_mensal = []
        saldo_acumulado = Decimal("0")
        for m in range(1, 13):
            rec_real = lookup.get(("RECEBER", m, "PAGO"), 0)
            pag_real = lookup.get(("PAGAR", m, "PAGO"), 0)
            rec_proj = lookup.get(("RECEBER", m, "ABERTO"), 0)
            pag_proj = lookup.get(("PAGAR", m, "ABERTO"), 0)
            saldo_mes = rec_real - pag_real
            saldo_acumulado += Decimal(str(saldo_mes))
            fluxo_mensal.append({
                "mes": m,
                "receber": rec_real,
                "pagar": pag_real,
                "receber_projetado": rec_proj,
                "pagar_projetado": pag_proj,
                "saldo": saldo_mes,
                "saldo_projetado": rec_proj - pag_proj,
                "saldo_acumulado": _d(saldo_acumulado),
            })
        return fluxo_mensal

    def _get_proximo_vencimento(self, parcelas_org, today):
        prox = (
            parcelas_org.filter(status="ABERTO", data_vencimento__gte=today)
            .select_related("lancamento")
            .order_by("data_vencimento")
            .first()
        )
        if not prox:
            return None
        return {
            "data": str(prox.data_vencimento),
            "descricao": prox.lancamento.descricao,
            "valor": _d(prox.valor_parcela_convertido),
            "tipo": prox.lancamento.tipo,
        }

    def _get_ultimas_transacoes(self, org):
        ultimas = (
            Lancamento.objects.filter(org=org)
            .select_related(
                "plano_de_contas", "plano_de_contas__grupo",
                "account", "contact", "forma_pagamento",
            )
            .prefetch_related("parcelas")
            .order_by("-created_at")[:10]
        )
        return LancamentoListSerializer(ultimas, many=True).data

    # ------------------------------------------------------------------
    # GET handler
    # ------------------------------------------------------------------

    def get(self, request):
        org = request.profile.org
        today = datetime.date.today()
        ano = _parse_int_param(request.query_params, "ano", today.year)
        mes = _parse_int_param(request.query_params, "mes", None)

        parcelas_org = Parcela.objects.filter(org=org)
        parcelas_ano = parcelas_org.filter(competencia_ano=ano)
        if mes:
            parcelas_ano = parcelas_ano.filter(competencia_mes=mes)

        kpis = self._get_kpis(parcelas_ano, parcelas_org, today)
        saldos = self._get_saldo_projetado(parcelas_org, ano, today)

        return Response({
            "ano": ano,
            "total_receber": _d(kpis["total_receber"]),
            "total_pagar": _d(kpis["total_pagar"]),
            "recebido_no_mes": _d(kpis["recebido_no_mes"]),
            "pago_no_mes": _d(kpis["pago_no_mes"]),
            "total_vencido": _d(kpis["total_vencido"]),
            "pct_vencidas": kpis["pct_vencidas"],
            "saldo": _d(kpis["saldo"]),
            "saldo_projetado": _d(saldos["saldo_projetado_ano"]),
            "saldo_projetado_mes": _d(saldos["saldo_projetado_mes"]),
            "saldo_projetado_ano": _d(saldos["saldo_projetado_ano"]),
            "proximo_vencimento": self._get_proximo_vencimento(parcelas_org, today),
            "fluxo_mensal": self._get_fluxo_mensal(parcelas_org, ano),
            "ultimas_transacoes": self._get_ultimas_transacoes(org),
        })


class FluxoPlanoContasReportView(APIView):
    """
    Pivot table: Plano de Contas x Meses.
    Each cell = sum of valor_parcela_convertido for that plano + month.
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org
        ano = _parse_int_param(request.query_params, "ano", datetime.date.today().year)
        tipo = request.query_params.get("tipo")

        # Single aggregated query instead of N×12 individual queries
        parcelas_qs = Parcela.objects.filter(
            org=org, competencia_ano=ano,
        ).exclude(status="CANCELADO")

        if tipo in ("RECEBER", "PAGAR"):
            parcelas_qs = parcelas_qs.filter(lancamento__tipo=tipo)

        agg_data = (
            parcelas_qs
            .values("lancamento__plano_de_contas_id", "competencia_mes")
            .annotate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))
        )

        # Build lookup: (plano_id, mes) → total
        lookup = {}
        for row in agg_data:
            key = (str(row["lancamento__plano_de_contas_id"]), row["competencia_mes"])
            lookup[key] = row["total"]

        planos = (
            PlanoDeContas.objects.filter(org=org, is_active=True)
            .select_related("grupo")
            .order_by("grupo__ordem", "grupo__codigo", "nome")
        )

        result = []
        for plano in planos:
            plano_id = str(plano.id)
            row = {
                "plano_id": plano_id,
                "plano_nome": plano.nome,
                "grupo_codigo": plano.grupo.codigo,
                "grupo_nome": plano.grupo.nome,
                "meses": {},
                "total": 0,
            }
            for m in range(1, 13):
                val = _d(lookup.get((plano_id, m), Decimal("0")))
                row["meses"][str(m)] = val
                row["total"] += val
            result.append(row)

        return Response({"ano": ano, "tipo": tipo, "planos": result})


class RelatorioMensalReportView(APIView):
    """
    Monthly report: 12 months of KPIs (receber, pagar, pago, saldo).
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org
        ano = _parse_int_param(request.query_params, "ano", datetime.date.today().year)

        # Single aggregated query instead of 48 individual queries
        agg_data = (
            Parcela.objects.filter(org=org, competencia_ano=ano)
            .exclude(status="CANCELADO")
            .values("competencia_mes", "lancamento__tipo", "status")
            .annotate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))
        )

        # Build lookup: (mes, tipo, status) → total
        lookup = {}
        for row in agg_data:
            key = (row["competencia_mes"], row["lancamento__tipo"], row["status"])
            lookup[key] = row["total"]

        def _get(mes, tipo, st):
            return lookup.get((mes, tipo, st), Decimal("0"))

        meses = []
        saldo_acumulado = Decimal("0")
        for m in range(1, 13):
            rec_aberto = _get(m, "RECEBER", "ABERTO")
            pag_aberto = _get(m, "PAGAR", "ABERTO")
            rec_pago = _get(m, "RECEBER", "PAGO")
            pag_pago = _get(m, "PAGAR", "PAGO")

            saldo_projetado = (rec_aberto + rec_pago) - (pag_aberto + pag_pago)
            saldo_acumulado += saldo_projetado

            meses.append({
                "mes": m,
                "receber_aberto": _d(rec_aberto),
                "pagar_aberto": _d(pag_aberto),
                "receber_pago": _d(rec_pago),
                "pagar_pago": _d(pag_pago),
                "saldo_pago": _d(rec_pago - pag_pago),
                "saldo_aberto": _d(rec_aberto - pag_aberto),
                "saldo_projetado": _d(saldo_projetado),
                "saldo_acumulado": _d(saldo_acumulado),
            })

        return Response({"ano": ano, "meses": meses})


class FluxoDiarioReportView(APIView):
    """
    Daily cash flow for a given month: day-by-day revenue vs expense
    with running accumulated balance. Useful for detecting days where
    the accumulated balance goes negative.
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org
        today = datetime.date.today()
        ano = _parse_int_param(request.query_params, "ano", today.year)
        mes = _parse_int_param(request.query_params, "mes", today.month)

        # Calculate last day of month
        if mes == 12:
            ultimo_dia = datetime.date(ano, 12, 31)
        else:
            ultimo_dia = datetime.date(ano, mes + 1, 1) - datetime.timedelta(days=1)
        num_dias = ultimo_dia.day

        parcelas_org = Parcela.objects.filter(org=org).exclude(status="CANCELADO")

        # PAGO parcelas: group by data_pagamento day
        pagos = (
            parcelas_org.filter(
                status="PAGO",
                data_pagamento__year=ano,
                data_pagamento__month=mes,
            )
            .values("lancamento__tipo", "data_pagamento")
            .annotate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))
        )

        # ABERTO parcelas: group by data_vencimento day
        abertos = (
            parcelas_org.filter(
                status="ABERTO",
                data_vencimento__year=ano,
                data_vencimento__month=mes,
            )
            .values("lancamento__tipo", "data_vencimento")
            .annotate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))
        )

        # Build daily lookup
        daily = {}
        for d in range(1, num_dias + 1):
            daily[d] = {"receita": Decimal("0"), "despesa": Decimal("0")}

        for row in pagos:
            dia = row["data_pagamento"].day
            if row["lancamento__tipo"] == "RECEBER":
                daily[dia]["receita"] += row["total"]
            else:
                daily[dia]["despesa"] += row["total"]

        for row in abertos:
            dia = row["data_vencimento"].day
            if row["lancamento__tipo"] == "RECEBER":
                daily[dia]["receita"] += row["total"]
            else:
                daily[dia]["despesa"] += row["total"]

        # Build response with running balance
        resultado = []
        saldo_acumulado = Decimal("0")
        total_receita = Decimal("0")
        total_despesa = Decimal("0")
        for d in range(1, num_dias + 1):
            rec = daily[d]["receita"]
            desp = daily[d]["despesa"]
            saldo_dia = rec - desp
            saldo_acumulado += saldo_dia
            total_receita += rec
            total_despesa += desp
            resultado.append({
                "dia": d,
                "data": str(datetime.date(ano, mes, d)),
                "receita": _d(rec),
                "despesa": _d(desp),
                "saldo_dia": _d(saldo_dia),
                "saldo_acumulado": _d(saldo_acumulado),
            })

        dias_negativos = [r for r in resultado if r["saldo_acumulado"] < 0]

        return Response(
            {
                "ano": ano,
                "mes": mes,
                "dias": resultado,
                "resumo": {
                    "total_receita": _d(total_receita),
                    "total_despesa": _d(total_despesa),
                    "saldo_final": _d(saldo_acumulado),
                    "dias_negativos": len(dias_negativos),
                    "primeiro_dia_negativo": (
                        dias_negativos[0]["dia"] if dias_negativos else None
                    ),
                },
            }
        )


class EntityFinancialReportView(APIView):
    """
    Financial summary for a CRM entity (Account, Contact, or Opportunity).
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    # Mapping entity_type → (parcela FK path, lancamento FK field)
    _ENTITY_FIELD_MAP = {
        "account": ("lancamento__account_id", "account_id"),
        "contact": ("lancamento__contact_id", "contact_id"),
        "opportunity": ("lancamento__opportunity_id", "opportunity_id"),
    }

    def get(self, request, pk):
        org = request.profile.org
        entity_type = request.query_params.get("entity_type", "account")

        if entity_type not in self._ENTITY_FIELD_MAP:
            return Response(
                {"detail": "entity_type must be account, contact, or opportunity"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parcela_fk, lanc_fk = self._ENTITY_FIELD_MAP[entity_type]

        # Consolidated aggregation (single query instead of 5)
        _SUM = lambda flt: Coalesce(  # noqa: E731
            Sum("valor_parcela_convertido", filter=flt), Decimal("0")
        )
        parcelas = Parcela.objects.filter(
            org=org, **{parcela_fk: pk}
        ).exclude(status="CANCELADO")

        agg = parcelas.aggregate(
            total_receber=_SUM(Q(lancamento__tipo="RECEBER")),
            total_pagar=_SUM(Q(lancamento__tipo="PAGAR")),
            total_pago=_SUM(Q(status="PAGO")),
            total_aberto=_SUM(Q(status="ABERTO")),
            total_vencido=_SUM(Q(status="ABERTO", data_vencimento__lt=datetime.date.today())),
        )

        lancamentos = (
            Lancamento.objects.filter(org=org, **{lanc_fk: pk})
            .order_by("-created_at")[:10]
        )

        return Response({
            "entity_type": entity_type,
            "entity_id": str(pk),
            "total_receber": _d(agg["total_receber"]),
            "total_pagar": _d(agg["total_pagar"]),
            "total_pago": _d(agg["total_pago"]),
            "total_aberto": _d(agg["total_aberto"]),
            "total_vencido": _d(agg["total_vencido"]),
            "saldo": _d(agg["total_receber"] - agg["total_pagar"]),
            "lancamentos": LancamentoListSerializer(lancamentos, many=True).data,
        })


class FormOptionsView(APIView):
    """Return form options for the frontend (planos, formas, accounts, contacts, etc.)."""

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org

        plano_grupos = PlanoDeContasGrupo.objects.filter(org=org, is_active=True)
        planos = PlanoDeContas.objects.filter(org=org, is_active=True).select_related("grupo")
        formas = FormaPagamento.objects.filter(org=org, is_active=True)
        accounts = Account.objects.filter(org=org)
        contacts = Contact.objects.filter(org=org)
        opportunities = Opportunity.objects.filter(org=org)

        return Response(
            {
                "plano_grupos": [
                    {"id": str(g.id), "codigo": g.codigo, "nome": g.nome}
                    for g in plano_grupos
                ],
                "planos": [
                    {
                        "id": str(p.id),
                        "nome": f"{p.grupo.codigo} / {p.nome}",
                        "grupo_id": str(p.grupo.id),
                    }
                    for p in planos
                ],
                "formas_pagamento": [
                    {"id": str(f.id), "nome": f.nome} for f in formas
                ],
                "accounts": [
                    {"id": str(a.id), "name": a.name} for a in accounts[:100]
                ],
                "contacts": [
                    {"id": str(c.id), "name": f"{c.first_name} {c.last_name}".strip(), "email": getattr(c, "email", "")}
                    for c in contacts[:100]
                ],
                "opportunities": [
                    {"id": str(o.id), "name": o.name} for o in opportunities[:100]
                ],
                "currencies": [
                    {"code": code, "label": label, "symbol": FINANCEIRO_CURRENCY_SYMBOLS.get(code, code)}
                    for code, label in FINANCEIRO_CURRENCY_CODES
                ],
                "org_currency": org.default_currency,
            }
        )


# =============================================================================
# PIX / Payment Transaction
# =============================================================================


class PaymentTransactionViewSet(FinanceiroMixin, ModelViewSet):
    """CRUD for PaymentTransaction (PIX and gateway payments)."""

    queryset = PaymentTransaction.objects.select_related(
        "invoice", "lancamento", "contact"
    )

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentTransactionCreateSerializer
        if self.action == "retrieve":
            return PaymentTransactionDetailSerializer
        return PaymentTransactionListSerializer

    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        status_filter = params.get("status")
        if status_filter in ("pending", "confirmed", "failed", "expired", "refunded"):
            qs = qs.filter(status=status_filter)

        tx_type = params.get("transaction_type")
        if tx_type in ("pix_qrcode", "pix_manual", "gateway"):
            qs = qs.filter(transaction_type=tx_type)

        date_from = _parse_date(params.get("date_from"))
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = _parse_date(params.get("date_to"))
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        invoice_id = _valid_uuid(params.get("invoice"))
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)

        lancamento_id = _valid_uuid(params.get("lancamento"))
        if lancamento_id:
            qs = qs.filter(lancamento_id=lancamento_id)

        search = params.get("search")
        if search:
            qs = qs.filter(
                Q(pix_txid__icontains=search)
                | Q(payer_name__icontains=search)
                | Q(gateway_reference__icontains=search)
            )

        return qs

    def perform_create(self, serializer):
        serializer.save(org=self.get_org())


# =============================================================================
# PIX QR Code Generation
# =============================================================================


class PixGenerateView(APIView):
    """
    POST /api/financeiro/pix/generate/

    Generate a PIX QR Code, creating a pending PaymentTransaction.
    Communicates with the configured PIX gateway for the org.
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def post(self, request):
        from financeiro.pix_gateway import (
            PixGatewayError,
            generate_pix_qrcode,
            get_pix_connection,
        )

        org = request.profile.org

        # Validate input
        serializer = PixGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = data["amount"]
        description = data.get("description", "")
        expiration_minutes = data.get("expiration_minutes", 30)
        invoice_id = data.get("invoice_id")
        lancamento_id = data.get("lancamento_id")
        contact_id = data.get("contact_id")

        # Get PIX gateway connection
        connection = get_pix_connection(org)
        if not connection:
            return Response(
                {"error": True, "errors": "Nenhum gateway PIX configurado e ativo para esta organização."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate QR Code via gateway
        try:
            result = generate_pix_qrcode(
                connection=connection,
                amount=amount,
                description=description,
                expiration_minutes=expiration_minutes,
            )
        except PixGatewayError as e:
            return Response(
                {"error": True, "errors": f"Erro no gateway PIX: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("Unexpected error generating PIX QR Code")
            return Response(
                {"error": True, "errors": "Erro inesperado ao gerar PIX."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Create pending PaymentTransaction
        transaction = PaymentTransaction(
            org=org,
            transaction_type="pix_qrcode",
            status="pending",
            amount=amount,
            currency="BRL",
            pix_txid=result["pix_txid"],
            expires_at=result["expires_at"],
            metadata_json={
                "description": description,
                "pix_copy_paste": result["pix_copy_paste"],
            },
        )
        if invoice_id:
            if not Invoice.objects.filter(id=invoice_id, org=org).exists():
                return Response(
                    {"error": True, "errors": "Invoice não encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            transaction.invoice_id = invoice_id
        if lancamento_id:
            if not Lancamento.objects.filter(id=lancamento_id, org=org).exists():
                return Response(
                    {"error": True, "errors": "Lançamento não encontrado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            transaction.lancamento_id = lancamento_id
        if contact_id:
            if not Contact.objects.filter(id=contact_id, org=org).exists():
                return Response(
                    {"error": True, "errors": "Contato não encontrado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            transaction.contact_id = contact_id

        transaction.save()

        return Response(
            {
                "error": False,
                "transaction_id": str(transaction.id),
                "pix_txid": result["pix_txid"],
                "qr_code_base64": result["qr_code_base64"],
                "pix_copy_paste": result["pix_copy_paste"],
                "expires_at": result["expires_at"].isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )
