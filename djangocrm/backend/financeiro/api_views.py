import datetime
import logging
from decimal import Decimal

from django.db.models import Case, Count, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from financeiro.constants import FINANCEIRO_CURRENCY_CODES, FINANCEIRO_CURRENCY_SYMBOLS
from financeiro.models import (
    FormaPagamento,
    Lancamento,
    Parcela,
    PaymentTransaction,
    PlanoDeContas,
    PlanoDeContasGrupo,
)
from financeiro.permissions import HasFinancialAccess
from common.permissions import HasOrgContext
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

logger = logging.getLogger(__name__)


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

        # Filters
        tipo = self.request.query_params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        plano = self.request.query_params.get("plano_de_contas")
        if plano:
            qs = qs.filter(plano_de_contas_id=plano)

        account = self.request.query_params.get("account")
        if account:
            qs = qs.filter(account_id=account)

        contact = self.request.query_params.get("contact")
        if contact:
            qs = qs.filter(contact_id=contact)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(descricao__icontains=search)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(data_primeiro_vencimento__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(data_primeiro_vencimento__lte=date_to)

        return qs

    def perform_create(self, serializer):
        org = self.get_org()
        data = serializer.validated_data

        # Auto-fetch exchange rate for VARIAVEL type
        if data.get("exchange_rate_type") == "VARIAVEL":
            if data.get("currency", "BRL") != org.default_currency:
                from financeiro.exchange_rates import ExchangeRateError, get_exchange_rate

                try:
                    rate = get_exchange_rate(
                        data["currency"],
                        org.default_currency,
                        data.get("data_primeiro_vencimento"),
                    )
                    lancamento = serializer.save(org=org, exchange_rate_to_base=rate)
                except ExchangeRateError as e:
                    from rest_framework.exceptions import ValidationError as DRFValidationError

                    raise DRFValidationError({"exchange_rate_to_base": str(e)})
            else:
                lancamento = serializer.save(org=org, exchange_rate_to_base=Decimal("1"))
        else:
            lancamento = serializer.save(org=org)

        lancamento.generate_parcelas()

    def perform_update(self, serializer):
        instance = serializer.instance
        data = serializer.validated_data

        # Check if financial fields changed (only possible with LancamentoFullUpdateSerializer)
        financial_fields = {
            "valor_total", "numero_parcelas", "data_primeiro_vencimento",
            "currency", "exchange_rate_to_base", "exchange_rate_type",
            "is_recorrente", "recorrencia_tipo",
        }
        financials_changed = bool(financial_fields & set(data.keys()))

        # If switching to VARIAVEL, fetch rate
        if data.get("exchange_rate_type") == "VARIAVEL":
            currency = data.get("currency", instance.currency)
            org = self.get_org()
            if currency != org.default_currency:
                from financeiro.exchange_rates import ExchangeRateError, get_exchange_rate

                try:
                    rate = get_exchange_rate(
                        currency,
                        org.default_currency,
                        data.get("data_primeiro_vencimento", instance.data_primeiro_vencimento),
                    )
                    data["exchange_rate_to_base"] = rate
                except ExchangeRateError as e:
                    from rest_framework.exceptions import ValidationError as DRFValidationError

                    raise DRFValidationError({"exchange_rate_to_base": str(e)})

        instance = serializer.save()

        # If financial fields changed and no paid parcelas, regenerate
        if financials_changed and not instance.parcelas.filter(status="PAGO").exists():
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
        # Cancel all open parcelas
        lancamento.parcelas.filter(status="ABERTO").update(status="CANCELADO")
        lancamento.update_status()
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

        tipo = self.request.query_params.get("tipo")
        if tipo:
            qs = qs.filter(lancamento__tipo=tipo)

        status_filter = self.request.query_params.get("status")
        if status_filter == "all":
            pass  # Show everything including CANCELADO
        elif status_filter:
            qs = qs.filter(status=status_filter)
        else:
            qs = qs.exclude(status="CANCELADO")

        account = self.request.query_params.get("account")
        if account:
            qs = qs.filter(lancamento__account_id=account)

        contact = self.request.query_params.get("contact")
        if contact:
            qs = qs.filter(lancamento__contact_id=contact)

        plano = self.request.query_params.get("plano_de_contas")
        if plano:
            qs = qs.filter(lancamento__plano_de_contas_id=plano)

        venc_from = self.request.query_params.get("vencimento_from")
        if venc_from:
            qs = qs.filter(data_vencimento__gte=venc_from)

        venc_to = self.request.query_params.get("vencimento_to")
        if venc_to:
            qs = qs.filter(data_vencimento__lte=venc_to)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(lancamento__descricao__icontains=search)

        # Ordering
        ordering = self.request.query_params.get("ordering", "data_vencimento")
        if ordering in (
            "data_vencimento",
            "-data_vencimento",
            "valor_parcela",
            "-valor_parcela",
            "status",
        ):
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

        ser = ParcelaPaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        parcela.data_pagamento = ser.validated_data.get(
            "data_pagamento", datetime.date.today()
        )
        parcela.save()
        parcela.lancamento.update_status()

        return Response(ParcelaSerializer(parcela).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        parcela = self.get_object()
        if parcela.status == "CANCELADO":
            return Response(
                {"detail": "Parcela já está cancelada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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

        parcelas = self.get_queryset().filter(
            id__in=parcela_ids, status="ABERTO"
        )

        updated_lancamentos = set()
        for parcela in parcelas:
            parcela.data_pagamento = data_pagamento
            parcela.save()
            updated_lancamentos.add(parcela.lancamento_id)

        # Update parent status
        for lanc in Lancamento.objects.filter(id__in=updated_lancamentos):
            lanc.update_status()

        return Response(
            {"detail": f"{parcelas.count()} parcelas marcadas como pagas."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Reports
# =============================================================================


class DashboardReportView(APIView):
    """
    Dashboard KPIs: total a receber, total a pagar, pago no mês,
    total vencido, % vencidas, saldo.
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org
        today = datetime.date.today()
        ano = int(request.query_params.get("ano", today.year))
        mes = request.query_params.get("mes")

        # Base querysets
        parcelas_org = Parcela.objects.filter(org=org)

        # Filter by competencia year
        parcelas_ano = parcelas_org.filter(competencia_ano=ano)

        if mes:
            mes = int(mes)
            parcelas_ano = parcelas_ano.filter(competencia_mes=mes)

        # KPIs
        total_receber = (
            parcelas_ano.filter(
                lancamento__tipo="RECEBER", status="ABERTO"
            ).aggregate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))["total"]
        )

        total_pagar = (
            parcelas_ano.filter(
                lancamento__tipo="PAGAR", status="ABERTO"
            ).aggregate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))["total"]
        )

        recebido_no_mes = (
            parcelas_org.filter(
                lancamento__tipo="RECEBER",
                data_pagamento__year=today.year,
                data_pagamento__month=today.month,
                status="PAGO",
            ).aggregate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))["total"]
        )

        pago_no_mes = (
            parcelas_org.filter(
                lancamento__tipo="PAGAR",
                data_pagamento__year=today.year,
                data_pagamento__month=today.month,
                status="PAGO",
            ).aggregate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))["total"]
        )

        total_vencido = (
            parcelas_org.filter(
                status="ABERTO", data_vencimento__lt=today
            ).aggregate(total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0")))["total"]
        )

        total_abertas = parcelas_ano.filter(status="ABERTO").count()
        total_vencidas_count = parcelas_org.filter(
            status="ABERTO", data_vencimento__lt=today
        ).count()
        pct_vencidas = (
            round((total_vencidas_count / total_abertas) * 100, 1)
            if total_abertas > 0
            else 0
        )

        saldo = recebido_no_mes - pago_no_mes

        # Monthly cash flow for the year
        fluxo_mensal = []
        for m in range(1, 13):
            receber_m = (
                parcelas_org.filter(
                    lancamento__tipo="RECEBER",
                    competencia_ano=ano,
                    competencia_mes=m,
                    status="PAGO",
                ).aggregate(
                    total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
                )["total"]
            )
            pagar_m = (
                parcelas_org.filter(
                    lancamento__tipo="PAGAR",
                    competencia_ano=ano,
                    competencia_mes=m,
                    status="PAGO",
                ).aggregate(
                    total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
                )["total"]
            )
            fluxo_mensal.append(
                {
                    "mes": m,
                    "receber": float(receber_m),
                    "pagar": float(pagar_m),
                    "saldo": float(receber_m - pagar_m),
                }
            )

        # Last 10 transactions
        ultimas = (
            Lancamento.objects.filter(org=org)
            .select_related(
                "plano_de_contas", "plano_de_contas__grupo",
                "account", "contact", "forma_pagamento",
            )
            .prefetch_related("parcelas")
            .order_by("-created_at")[:10]
        )
        ultimas_data = LancamentoListSerializer(ultimas, many=True).data

        return Response(
            {
                "ano": ano,
                "total_receber": float(total_receber),
                "total_pagar": float(total_pagar),
                "recebido_no_mes": float(recebido_no_mes),
                "pago_no_mes": float(pago_no_mes),
                "total_vencido": float(total_vencido),
                "pct_vencidas": pct_vencidas,
                "saldo": float(saldo),
                "fluxo_mensal": fluxo_mensal,
                "ultimas_transacoes": ultimas_data,
            }
        )


class FluxoPlanoContasReportView(APIView):
    """
    Pivot table: Plano de Contas x Meses.
    Each cell = sum of valor_parcela_convertido for that plano + month.
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org
        ano = int(request.query_params.get("ano", datetime.date.today().year))
        tipo = request.query_params.get("tipo")

        parcelas = Parcela.objects.filter(
            org=org, competencia_ano=ano
        ).exclude(status="CANCELADO").select_related("lancamento__plano_de_contas__grupo")

        if tipo:
            parcelas = parcelas.filter(lancamento__tipo=tipo)

        # Build pivot
        planos = (
            PlanoDeContas.objects.filter(org=org, is_active=True)
            .select_related("grupo")
            .order_by("grupo__ordem", "grupo__codigo", "nome")
        )

        result = []
        for plano in planos:
            row = {
                "plano_id": str(plano.id),
                "plano_nome": plano.nome,
                "grupo_codigo": plano.grupo.codigo,
                "grupo_nome": plano.grupo.nome,
                "meses": {},
                "total": 0,
            }
            for m in range(1, 13):
                val = (
                    parcelas.filter(
                        lancamento__plano_de_contas=plano, competencia_mes=m
                    ).aggregate(
                        total=Coalesce(
                            Sum("valor_parcela_convertido"), Decimal("0")
                        )
                    )["total"]
                )
                row["meses"][str(m)] = float(val)
                row["total"] += float(val)

            result.append(row)

        return Response({"ano": ano, "tipo": tipo, "planos": result})


class RelatorioMensalReportView(APIView):
    """
    Monthly report: 12 months of KPIs (receber, pagar, pago, saldo).
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org
        ano = int(request.query_params.get("ano", datetime.date.today().year))

        parcelas = Parcela.objects.filter(org=org, competencia_ano=ano).exclude(status="CANCELADO")

        meses = []
        for m in range(1, 13):
            p_mes = parcelas.filter(competencia_mes=m)

            receber_aberto = (
                p_mes.filter(lancamento__tipo="RECEBER", status="ABERTO").aggregate(
                    total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
                )["total"]
            )
            pagar_aberto = (
                p_mes.filter(lancamento__tipo="PAGAR", status="ABERTO").aggregate(
                    total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
                )["total"]
            )
            receber_pago = (
                p_mes.filter(lancamento__tipo="RECEBER", status="PAGO").aggregate(
                    total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
                )["total"]
            )
            pagar_pago = (
                p_mes.filter(lancamento__tipo="PAGAR", status="PAGO").aggregate(
                    total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
                )["total"]
            )

            meses.append(
                {
                    "mes": m,
                    "receber_aberto": float(receber_aberto),
                    "pagar_aberto": float(pagar_aberto),
                    "receber_pago": float(receber_pago),
                    "pagar_pago": float(pagar_pago),
                    "saldo_pago": float(receber_pago - pagar_pago),
                    "saldo_aberto": float(receber_aberto - pagar_aberto),
                }
            )

        return Response({"ano": ano, "meses": meses})


class EntityFinancialReportView(APIView):
    """
    Financial summary for a CRM entity (Account, Contact, or Opportunity).
    """

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request, pk):
        org = request.profile.org
        entity_type = request.query_params.get("entity_type", "account")

        filter_kwargs = {"org": org}
        if entity_type == "account":
            filter_kwargs["lancamento__account_id"] = pk
        elif entity_type == "contact":
            filter_kwargs["lancamento__contact_id"] = pk
        elif entity_type == "opportunity":
            filter_kwargs["lancamento__opportunity_id"] = pk
        else:
            return Response(
                {"detail": "entity_type must be account, contact, or opportunity"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parcelas = Parcela.objects.filter(**filter_kwargs).exclude(status="CANCELADO")

        total_receber = (
            parcelas.filter(lancamento__tipo="RECEBER").aggregate(
                total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
            )["total"]
        )
        total_pagar = (
            parcelas.filter(lancamento__tipo="PAGAR").aggregate(
                total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
            )["total"]
        )
        total_pago = (
            parcelas.filter(status="PAGO").aggregate(
                total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
            )["total"]
        )
        total_aberto = (
            parcelas.filter(status="ABERTO").aggregate(
                total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
            )["total"]
        )
        total_vencido = (
            parcelas.filter(
                status="ABERTO", data_vencimento__lt=datetime.date.today()
            ).aggregate(
                total=Coalesce(Sum("valor_parcela_convertido"), Decimal("0"))
            )["total"]
        )

        # Recent lancamentos for this entity
        lanc_filter = {"org": org}
        if entity_type == "account":
            lanc_filter["account_id"] = pk
        elif entity_type == "contact":
            lanc_filter["contact_id"] = pk
        elif entity_type == "opportunity":
            lanc_filter["opportunity_id"] = pk

        lancamentos = Lancamento.objects.filter(**lanc_filter).order_by("-created_at")[:10]
        lancamentos_data = LancamentoListSerializer(lancamentos, many=True).data

        return Response(
            {
                "entity_type": entity_type,
                "entity_id": str(pk),
                "total_receber": float(total_receber),
                "total_pagar": float(total_pagar),
                "total_pago": float(total_pago),
                "total_aberto": float(total_aberto),
                "total_vencido": float(total_vencido),
                "saldo": float(total_receber - total_pagar),
                "lancamentos": lancamentos_data,
            }
        )


class FormOptionsView(APIView):
    """Return form options for the frontend (planos, formas, accounts, contacts, etc.)."""

    permission_classes = [IsAuthenticated, HasOrgContext, HasFinancialAccess]

    def get(self, request):
        org = request.profile.org

        from accounts.models import Account
        from contacts.models import Contact
        from opportunity.models import Opportunity
        from invoices.models import Invoice

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

    def get_queryset(self):
        qs = super().get_queryset()

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        tx_type = self.request.query_params.get("transaction_type")
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        invoice_id = self.request.query_params.get("invoice")
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)

        lancamento_id = self.request.query_params.get("lancamento")
        if lancamento_id:
            qs = qs.filter(lancamento_id=lancamento_id)

        search = self.request.query_params.get("search")
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
            from invoices.models import Invoice
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
            from contacts.models import Contact
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
