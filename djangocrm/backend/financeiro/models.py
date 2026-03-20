import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.base import BaseOrgModel
from financeiro.constants import (
    EXCHANGE_RATE_TYPES,
    FINANCEIRO_CURRENCY_CODES,
    LANCAMENTO_STATUS,
    LANCAMENTO_TIPOS,
    PARCELA_STATUS,
    RECORRENCIA_TIPOS,
    TRANSACTION_STATUS,
    TRANSACTION_TYPES,
)


APPLIES_TO_CHOICES = [
    ("AMBOS", "Ambos"),
    ("PAGAR", "Pagar"),
    ("RECEBER", "Receber"),
]


class PlanoDeContasGrupo(BaseOrgModel):
    """
    Grupo do Plano de Contas / Centro de Custo.
    """

    codigo = models.CharField(max_length=20, help_text="Código do grupo (ex: 1.1, 2.1)")
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0, help_text="Ordem de exibição")
    color = models.CharField(max_length=7, default="#6B7280", help_text="Cor hex para exibição no frontend")
    applies_to = models.CharField(
        max_length=10, choices=APPLIES_TO_CHOICES, default="AMBOS",
        help_text="Tipo de lançamento ao qual este grupo se aplica",
    )
    is_system_default = models.BooleanField(default=False, help_text="Grupos padrão do sistema não podem ser deletados")

    class Meta:
        db_table = "financeiro_plano_grupo"
        ordering = ["ordem", "codigo"]
        unique_together = [["codigo", "org"]]
        verbose_name = "Grupo do Plano de Contas"
        verbose_name_plural = "Grupos do Plano de Contas"

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class PlanoDeContas(BaseOrgModel):
    """
    Conta dentro de um grupo do Plano de Contas / Centro de Custo.
    """

    grupo = models.ForeignKey(
        PlanoDeContasGrupo,
        on_delete=models.CASCADE,
        related_name="contas",
    )
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    code = models.CharField(max_length=20, blank=True, default="", help_text="Código interno opcional")
    is_system_default = models.BooleanField(default=False, help_text="Contas padrão do sistema não podem ser deletadas")
    sort_order = models.PositiveIntegerField(default=0, help_text="Ordem de exibição dentro do grupo")

    class Meta:
        db_table = "financeiro_plano_contas"
        ordering = ["grupo__ordem", "grupo__codigo", "sort_order", "nome"]
        unique_together = [["grupo", "nome", "org"]]
        verbose_name = "Plano de Contas"
        verbose_name_plural = "Planos de Contas"

    def __str__(self):
        return f"{self.grupo.codigo} / {self.nome}"


class FormaPagamento(BaseOrgModel):
    """
    Formas de pagamento (ex: PIX, Boleto, Crypto Wallet).
    """

    nome = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "financeiro_forma_pagamento"
        ordering = ["nome"]
        unique_together = [["nome", "org"]]
        verbose_name = "Forma de Pagamento"
        verbose_name_plural = "Formas de Pagamento"

    def __str__(self):
        return self.nome


class Lancamento(BaseOrgModel):
    """
    Transação principal — Conta a Pagar ou Conta a Receber.
    Gera automaticamente N parcelas ao ser criado.
    """

    tipo = models.CharField(max_length=10, choices=LANCAMENTO_TIPOS)
    descricao = models.CharField(max_length=500)
    observacoes = models.TextField(blank=True, default="")

    plano_de_contas = models.ForeignKey(
        PlanoDeContas,
        on_delete=models.PROTECT,
        related_name="lancamentos",
        null=True,
        blank=True,
    )

    # CRM entity links
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    opportunity = models.ForeignKey(
        "opportunity.Opportunity",
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "invoices.Product",
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
        help_text="Produto/serviço associado (opcional)",
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=1,
        help_text="Quantidade do produto/serviço",
    )

    # Currency & values
    currency = models.CharField(
        max_length=5, choices=FINANCEIRO_CURRENCY_CODES, default="BRL"
    )
    valor_total = models.DecimalField(
        max_digits=18, decimal_places=8, help_text="Valor na moeda original"
    )
    exchange_rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=Decimal("1"),
        help_text="1 unidade da moeda = X unidades da moeda base da org",
    )
    valor_convertido = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Valor convertido para moeda base da org (auto-calculado)",
    )

    # Exchange rate type
    exchange_rate_type = models.CharField(
        max_length=10,
        choices=EXCHANGE_RATE_TYPES,
        default="FIXO",
        help_text="FIXO = manual, VARIAVEL = busca automática da API",
    )

    # Recurring
    is_recorrente = models.BooleanField(default=False)
    recorrencia_tipo = models.CharField(
        max_length=15, choices=RECORRENCIA_TIPOS, null=True, blank=True
    )
    data_fim_recorrencia = models.DateField(null=True, blank=True)
    recorrencia_ativa = models.BooleanField(default=True)

    # Payment
    forma_pagamento = models.ForeignKey(
        FormaPagamento,
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    numero_parcelas = models.PositiveIntegerField(default=1)
    data_primeiro_vencimento = models.DateField()

    # Status (derived from parcelas)
    status = models.CharField(
        max_length=10, choices=LANCAMENTO_STATUS, default="ABERTO"
    )

    # Competência
    competencia_ano = models.IntegerField(null=True, blank=True)
    competencia_mes = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "financeiro_lancamento"
        ordering = ["-data_primeiro_vencimento", "-created_at"]
        verbose_name = "Lançamento"
        verbose_name_plural = "Lançamentos"
        indexes = [
            models.Index(fields=["org", "tipo"]),
            models.Index(fields=["org", "status"]),
            models.Index(fields=["org", "tipo", "status"]),
            models.Index(fields=["org", "competencia_ano", "competencia_mes"]),
            models.Index(fields=["account"]),
            models.Index(fields=["contact"]),
            models.Index(fields=["plano_de_contas"]),
            models.Index(fields=["data_primeiro_vencimento"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.descricao or ''} ({self.currency} {self.valor_total})"

    def save(self, *args, **kwargs):
        # Auto-calculate valor_convertido
        self.valor_convertido = (
            self.valor_total * self.exchange_rate_to_base
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Auto-calculate competência from first installment date
        if self.data_primeiro_vencimento:
            self.competencia_ano = self.data_primeiro_vencimento.year
            self.competencia_mes = self.data_primeiro_vencimento.month

        super().save(*args, **kwargs)

    def generate_parcelas(self):
        """
        Generate installments. Delegates to recurring method if applicable.
        """
        if self.parcelas.exists():
            return

        if self.is_recorrente:
            self.generate_recurring_parcelas()
            return

        n = self.numero_parcelas
        valor_each = (self.valor_total / n).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        remainder = self.valor_total - (valor_each * (n - 1))

        parcelas = []
        sum_converted = Decimal("0")
        for i in range(n):
            # Monthly offset
            month_offset = i
            year = self.data_primeiro_vencimento.year + (
                (self.data_primeiro_vencimento.month + month_offset - 1) // 12
            )
            month = (
                (self.data_primeiro_vencimento.month + month_offset - 1) % 12
            ) + 1
            day = min(self.data_primeiro_vencimento.day, _last_day_of_month(year, month))
            vencimento = datetime.date(year, month, day)

            valor = remainder if i == n - 1 else valor_each

            if i == n - 1:
                # Last parcela: adjust converted value so sum matches lancamento total
                converted = self.valor_convertido - sum_converted
            else:
                converted = (
                    valor * self.exchange_rate_to_base
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                sum_converted += converted

            parcelas.append(
                Parcela(
                    lancamento=self,
                    numero=i + 1,
                    valor_parcela=valor,
                    valor_parcela_convertido=converted,
                    currency=self.currency,
                    exchange_rate_to_base=self.exchange_rate_to_base,
                    data_vencimento=vencimento,
                    status="ABERTO",
                    competencia_ano=vencimento.year,
                    competencia_mes=vencimento.month,
                    org=self.org,
                )
            )

        Parcela.objects.bulk_create(parcelas)

    def generate_recurring_parcelas(self, months_ahead=12):
        """
        Generate parcelas for recurring lancamentos.
        Each parcela = full valor_total (not divided).
        Generates up to months_ahead months into the future (default 12).
        Called on creation and periodically by Celery to extend the window.
        """
        import calendar

        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=months_ahead * 31)

        # If data_fim_recorrencia is set, cap at that date
        if self.data_fim_recorrencia and self.data_fim_recorrencia < target_date:
            target_date = self.data_fim_recorrencia

        # Find last existing parcela number and date
        last_parcela = self.parcelas.order_by("-numero").first()
        if last_parcela:
            next_numero = last_parcela.numero + 1
            last_date = last_parcela.data_vencimento
        else:
            next_numero = 1
            last_date = None

        # Calculate interval
        tipo = self.recorrencia_tipo or "MENSAL"

        def next_date(base_date):
            if tipo == "SEMANAL":
                return base_date + datetime.timedelta(weeks=1)
            elif tipo == "QUINZENAL":
                return base_date + datetime.timedelta(weeks=2)
            elif tipo == "ANUAL":
                y = base_date.year + 1
                m = base_date.month
                d = min(base_date.day, calendar.monthrange(y, m)[1])
                return datetime.date(y, m, d)
            else:  # MENSAL
                y = base_date.year + ((base_date.month) // 12)
                m = (base_date.month % 12) + 1
                d = min(base_date.day, calendar.monthrange(y, m)[1])
                return datetime.date(y, m, d)

        # Starting date for new parcelas
        if last_date:
            current_date = next_date(last_date)
        else:
            current_date = self.data_primeiro_vencimento

        parcelas = []
        while current_date <= target_date:
            rate = self.exchange_rate_to_base
            valor_convertido = (
                self.valor_total * rate
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            parcelas.append(
                Parcela(
                    lancamento=self,
                    numero=next_numero,
                    valor_parcela=self.valor_total,
                    valor_parcela_convertido=valor_convertido,
                    currency=self.currency,
                    exchange_rate_to_base=rate,
                    data_vencimento=current_date,
                    status="ABERTO",
                    competencia_ano=current_date.year,
                    competencia_mes=current_date.month,
                    org=self.org,
                )
            )
            next_numero += 1
            current_date = next_date(current_date)

        if parcelas:
            Parcela.objects.bulk_create(parcelas)
            # Update numero_parcelas to reflect actual count
            total = self.parcelas.count() + len(parcelas)
            if self.numero_parcelas != total:
                self.numero_parcelas = total
                self.save(update_fields=["numero_parcelas", "updated_at"])

    def update_status(self):
        """Recalculate status from parcelas."""
        parcelas = self.parcelas.all()
        if not parcelas.exists():
            return

        total = parcelas.count()
        pagas = parcelas.filter(status="PAGO").count()
        canceladas = parcelas.filter(status="CANCELADO").count()

        if canceladas == total:
            new_status = "CANCELADO"
        elif pagas == total:
            new_status = "PAGO"
        elif pagas + canceladas == total:
            new_status = "PAGO"
        else:
            new_status = "ABERTO"

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class Parcela(BaseOrgModel):
    """
    Parcela individual de um lançamento.
    """

    lancamento = models.ForeignKey(
        Lancamento, on_delete=models.CASCADE, related_name="parcelas"
    )
    numero = models.PositiveIntegerField()
    valor_parcela = models.DecimalField(
        max_digits=18, decimal_places=8, help_text="Valor na moeda original"
    )
    valor_parcela_convertido = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    currency = models.CharField(max_length=5, choices=FINANCEIRO_CURRENCY_CODES)
    exchange_rate_to_base = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal("1")
    )
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=PARCELA_STATUS, default="ABERTO"
    )
    competencia_ano = models.IntegerField(null=True, blank=True)
    competencia_mes = models.IntegerField(null=True, blank=True)
    observacoes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "financeiro_parcela"
        ordering = ["lancamento", "numero"]
        unique_together = [["lancamento", "numero"]]
        verbose_name = "Parcela"
        verbose_name_plural = "Parcelas"
        indexes = [
            models.Index(fields=["org", "status"]),
            models.Index(fields=["org", "data_vencimento"]),
            models.Index(fields=["org", "status", "data_vencimento"]),
            models.Index(fields=["org", "competencia_ano", "competencia_mes"]),
        ]

    def __str__(self):
        return f"Parcela {self.numero}/{self.lancamento.numero_parcelas} - {self.lancamento.descricao}"

    def save(self, *args, **kwargs):
        # Auto-derive status from data_pagamento
        if self.data_pagamento and self.status != "CANCELADO":
            self.status = "PAGO"

        # Auto-calculate valor_parcela_convertido
        self.valor_parcela_convertido = (
            self.valor_parcela * self.exchange_rate_to_base
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)

    @property
    def dias_atraso(self):
        """Days overdue (0 if not overdue or already paid)."""
        if self.status != "ABERTO":
            return 0
        today = datetime.date.today()
        if today > self.data_vencimento:
            return (today - self.data_vencimento).days
        return 0

    @property
    def pago_atrasado(self):
        """True if paid after the due date."""
        if self.status == "PAGO" and self.data_pagamento:
            return self.data_pagamento > self.data_vencimento
        return False

    @property
    def status_message(self):
        """Human-readable status message in pt-BR."""
        if self.status == "CANCELADO":
            return "Cancelada"
        if self.status == "PAGO":
            is_receber = self.lancamento.tipo == "RECEBER"
            if self.pago_atrasado:
                return "Recebida com atraso" if is_receber else "Paga com atraso"
            return "Recebida" if is_receber else "Paga"
        # ABERTO
        dias = self.dias_atraso
        if dias > 0:
            return f"Vencida há {dias} dia{'s' if dias != 1 else ''}"
        if dias == 0 and self.data_vencimento == datetime.date.today():
            return "Vence hoje"
        return "Em aberto"


def _last_day_of_month(year, month):
    """Return the last day of a given month."""
    import calendar

    return calendar.monthrange(year, month)[1]


# =============================================================================
# PIX / Payment Transaction
# =============================================================================


class PaymentTransaction(BaseOrgModel):
    """
    Transação de pagamento PIX ou gateway.

    Campos sensíveis (payer_document) são criptografados com Fernet no save()
    e descriptografados sob demanda via property.
    """

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )
    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS,
        default="pending",
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    currency = models.CharField(max_length=5, default="BRL")

    # PIX-specific
    pix_txid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Identificador único da transação PIX",
    )
    pix_e2e_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="End-to-end ID do PIX (preenchido na confirmação)",
    )

    # Gateway-specific
    gateway_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Referência do gateway de pagamento",
    )

    # Timestamps
    paid_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Payer info
    payer_name = models.CharField(max_length=255, null=True, blank=True)
    _payer_document = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_column="payer_document",
        help_text="CPF/CNPJ criptografado com Fernet",
    )

    # Metadata
    metadata_json = models.JSONField(default=dict, blank=True)

    # FK relationships (all optional)
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pix_transactions",
    )
    lancamento = models.ForeignKey(
        Lancamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pix_transactions",
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pix_transactions",
    )

    class Meta:
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"
        db_table = "payment_transaction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["org", "status"]),
            models.Index(fields=["org", "transaction_type"]),
            models.Index(fields=["pix_txid"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="payment_transaction_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["org", "pix_txid"],
                name="payment_transaction_pix_txid_unique_per_org",
                condition=models.Q(pix_txid__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.currency} {self.amount} ({self.status})"

    # --- Fernet encryption for payer_document ---

    @staticmethod
    def _get_fernet():
        from cryptography.fernet import Fernet
        from django.conf import settings

        fernet_key = getattr(settings, "FERNET_KEY", None)
        if not fernet_key:
            return None
        return Fernet(
            fernet_key.encode() if isinstance(fernet_key, str) else fernet_key
        )

    @property
    def payer_document(self):
        """Decrypt payer_document on read."""
        raw = self._payer_document
        if not raw:
            return None
        f = self._get_fernet()
        if not f:
            return raw
        try:
            return f.decrypt(raw.encode()).decode()
        except Exception:
            return raw  # fallback if decryption fails

    @payer_document.setter
    def payer_document(self, value):
        """Encrypt payer_document on write."""
        if not value:
            self._payer_document = None
            return
        f = self._get_fernet()
        if f and not value.startswith("gAAAAA"):
            self._payer_document = f.encrypt(value.encode()).decode()
        else:
            self._payer_document = value
