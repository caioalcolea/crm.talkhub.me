from decimal import Decimal

from rest_framework import serializers

from financeiro.constants import FINANCEIRO_CURRENCY_CODES, FINANCEIRO_CURRENCY_SYMBOLS
from financeiro.models import (
    FormaPagamento,
    Lancamento,
    Parcela,
    PaymentTransaction,
    PlanoDeContas,
    PlanoDeContasGrupo,
)


# =============================================================================
# Plano de Contas
# =============================================================================


class PlanoDeContasGrupoSerializer(serializers.ModelSerializer):
    contas_count = serializers.SerializerMethodField()

    class Meta:
        model = PlanoDeContasGrupo
        fields = [
            "id",
            "codigo",
            "nome",
            "descricao",
            "is_active",
            "ordem",
            "color",
            "applies_to",
            "is_system_default",
            "contas_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "contas_count", "is_system_default"]

    def get_contas_count(self, obj):
        return obj.contas.filter(is_active=True).count()


class PlanoDeContasSerializer(serializers.ModelSerializer):
    grupo_nome = serializers.CharField(source="grupo.nome", read_only=True)
    grupo_codigo = serializers.CharField(source="grupo.codigo", read_only=True)

    class Meta:
        model = PlanoDeContas
        fields = [
            "id",
            "grupo",
            "grupo_nome",
            "grupo_codigo",
            "nome",
            "descricao",
            "is_active",
            "code",
            "is_system_default",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "is_system_default"]


class PlanoDeContasGrupoTreeSerializer(serializers.ModelSerializer):
    """Grupo with nested contas for tree view."""

    contas = PlanoDeContasSerializer(many=True, read_only=True)

    class Meta:
        model = PlanoDeContasGrupo
        fields = [
            "id",
            "codigo",
            "nome",
            "descricao",
            "is_active",
            "ordem",
            "color",
            "applies_to",
            "is_system_default",
            "contas",
        ]


# =============================================================================
# Forma de Pagamento
# =============================================================================


class FormaPagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormaPagamento
        fields = ["id", "nome", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


# =============================================================================
# Parcela
# =============================================================================


class ParcelaSerializer(serializers.ModelSerializer):
    lancamento_descricao = serializers.CharField(
        source="lancamento.descricao", read_only=True
    )
    lancamento_tipo = serializers.CharField(
        source="lancamento.tipo", read_only=True
    )
    total_parcelas = serializers.IntegerField(
        source="lancamento.numero_parcelas", read_only=True
    )
    account_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    dias_atraso = serializers.IntegerField(read_only=True)
    pago_atrasado = serializers.BooleanField(read_only=True)
    status_message = serializers.CharField(read_only=True)
    currency_symbol = serializers.SerializerMethodField()

    class Meta:
        model = Parcela
        fields = [
            "id",
            "lancamento",
            "lancamento_descricao",
            "lancamento_tipo",
            "numero",
            "total_parcelas",
            "valor_parcela",
            "valor_parcela_convertido",
            "currency",
            "currency_symbol",
            "exchange_rate_to_base",
            "data_vencimento",
            "data_pagamento",
            "status",
            "competencia_ano",
            "competencia_mes",
            "observacoes",
            "account_name",
            "contact_name",
            "dias_atraso",
            "pago_atrasado",
            "status_message",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "lancamento_descricao",
            "lancamento_tipo",
            "total_parcelas",
            "account_name",
            "contact_name",
            "dias_atraso",
            "pago_atrasado",
            "status_message",
            "currency_symbol",
            "created_at",
        ]

    def get_account_name(self, obj):
        acc = obj.lancamento.account
        return acc.name if acc else None

    def get_contact_name(self, obj):
        ct = obj.lancamento.contact
        if ct:
            return f"{ct.first_name} {ct.last_name}".strip()
        return None

    def get_currency_symbol(self, obj):
        return FINANCEIRO_CURRENCY_SYMBOLS.get(obj.currency, obj.currency)


class ParcelaPaySerializer(serializers.Serializer):
    data_pagamento = serializers.DateField(required=False)


class ParcelaBulkPaySerializer(serializers.Serializer):
    parcela_ids = serializers.ListField(child=serializers.UUIDField())
    data_pagamento = serializers.DateField(required=False)


# =============================================================================
# Lancamento
# =============================================================================


class LancamentoListSerializer(serializers.ModelSerializer):
    plano_de_contas_nome = serializers.SerializerMethodField()
    forma_pagamento_nome = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    parcelas_pagas = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    can_edit_financials = serializers.SerializerMethodField()
    valor_parcela_display = serializers.SerializerMethodField()
    recorrencia_label = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Lancamento
        fields = [
            "id",
            "tipo",
            "descricao",
            "plano_de_contas",
            "plano_de_contas_nome",
            "account",
            "account_name",
            "contact",
            "contact_name",
            "opportunity",
            "invoice",
            "product",
            "product_name",
            "quantity",
            "currency",
            "currency_symbol",
            "valor_total",
            "valor_convertido",
            "exchange_rate_to_base",
            "exchange_rate_type",
            "forma_pagamento",
            "forma_pagamento_nome",
            "numero_parcelas",
            "data_primeiro_vencimento",
            "status",
            "competencia_ano",
            "competencia_mes",
            "parcelas_pagas",
            "is_recorrente",
            "recorrencia_tipo",
            "data_fim_recorrencia",
            "recorrencia_ativa",
            "can_edit_financials",
            "valor_parcela_display",
            "recorrencia_label",
            "created_at",
        ]

    def get_plano_de_contas_nome(self, obj):
        return str(obj.plano_de_contas) if obj.plano_de_contas else None

    def get_forma_pagamento_nome(self, obj):
        return obj.forma_pagamento.nome if obj.forma_pagamento else None

    def get_account_name(self, obj):
        return obj.account.name if obj.account else None

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}".strip()
        return None

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_parcelas_pagas(self, obj):
        pagas = obj.parcelas.filter(status="PAGO").count()
        return f"{pagas}/{obj.numero_parcelas}"

    def get_currency_symbol(self, obj):
        return FINANCEIRO_CURRENCY_SYMBOLS.get(obj.currency, obj.currency)

    def get_can_edit_financials(self, obj):
        """True if no parcelas have been paid and lancamento is not cancelled."""
        if obj.status == "CANCELADO":
            return False
        return not obj.parcelas.filter(status="PAGO").exists()

    def get_valor_parcela_display(self, obj):
        """Value per parcela: for recurring = valor_total, for installments = valor_total / n."""
        if obj.is_recorrente:
            return str(obj.valor_convertido)
        if obj.numero_parcelas and obj.numero_parcelas > 1:
            return str((obj.valor_convertido / obj.numero_parcelas).quantize(Decimal("0.01")))
        return str(obj.valor_convertido)

    RECORRENCIA_LABELS = {
        "MENSAL": "Mensal",
        "QUINZENAL": "Quinzenal",
        "SEMANAL": "Semanal",
        "ANUAL": "Anual",
    }

    def get_recorrencia_label(self, obj):
        """Human label for recurrence: 'Mensal', 'Mensal (parado)', or null."""
        if not obj.is_recorrente:
            return None
        label = self.RECORRENCIA_LABELS.get(obj.recorrencia_tipo, obj.recorrencia_tipo or "Recorrente")
        if not obj.recorrencia_ativa:
            label += " (parado)"
        return label


class LancamentoDetailSerializer(LancamentoListSerializer):
    parcelas = ParcelaSerializer(many=True, read_only=True)
    reminder_policies = serializers.SerializerMethodField()

    class Meta(LancamentoListSerializer.Meta):
        fields = LancamentoListSerializer.Meta.fields + [
            "observacoes",
            "parcelas",
            "reminder_policies",
        ]

    def get_reminder_policies(self, obj):
        from django.contrib.contenttypes.models import ContentType
        from assistant.models import ReminderPolicy
        ct = ContentType.objects.get_for_model(obj)
        policies = ReminderPolicy.objects.filter(
            target_content_type=ct, target_object_id=obj.id
        )
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "is_active": p.is_active,
                "trigger_type": p.trigger_type,
                "trigger_config": p.trigger_config,
                "channel_config": p.channel_config,
                "next_run_at": p.next_run_at.isoformat() if p.next_run_at else None,
                "run_count": p.run_count,
            }
            for p in policies
        ]


class LancamentoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lancamento
        fields = [
            "tipo",
            "descricao",
            "observacoes",
            "plano_de_contas",
            "account",
            "contact",
            "opportunity",
            "invoice",
            "product",
            "quantity",
            "currency",
            "valor_total",
            "exchange_rate_to_base",
            "exchange_rate_type",
            "forma_pagamento",
            "numero_parcelas",
            "data_primeiro_vencimento",
            "is_recorrente",
            "recorrencia_tipo",
            "data_fim_recorrencia",
        ]

    def validate_valor_total(self, value):
        if value <= 0:
            raise serializers.ValidationError("Valor total deve ser positivo.")
        return value

    def validate_numero_parcelas(self, value):
        if value < 1:
            raise serializers.ValidationError("Numero de parcelas deve ser ao menos 1.")
        if value > 120:
            raise serializers.ValidationError("Maximo de 120 parcelas.")
        return value

    def validate_quantity(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Quantidade deve ser positiva.")
        return value

    def validate_exchange_rate_to_base(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Taxa de câmbio deve ser positiva.")
        return value

    def validate(self, data):
        if data.get("is_recorrente") and not data.get("recorrencia_tipo"):
            raise serializers.ValidationError({
                "recorrencia_tipo": "Tipo de recorrencia e obrigatorio para lancamentos recorrentes."
            })
        return data


class LancamentoUpdateSerializer(serializers.ModelSerializer):
    """Update serializer for lancamentos with some paid parcelas (metadata only)."""

    class Meta:
        model = Lancamento
        fields = [
            "descricao",
            "observacoes",
            "plano_de_contas",
            "account",
            "contact",
            "opportunity",
            "invoice",
            "forma_pagamento",
        ]


class LancamentoFullUpdateSerializer(serializers.ModelSerializer):
    """Update serializer for lancamentos with NO paid parcelas (can change financials)."""

    class Meta:
        model = Lancamento
        fields = [
            "descricao",
            "observacoes",
            "plano_de_contas",
            "account",
            "contact",
            "opportunity",
            "invoice",
            "product",
            "quantity",
            "forma_pagamento",
            "valor_total",
            "numero_parcelas",
            "data_primeiro_vencimento",
            "currency",
            "exchange_rate_to_base",
            "exchange_rate_type",
            "is_recorrente",
            "recorrencia_tipo",
            "data_fim_recorrencia",
            "recorrencia_ativa",
        ]

    def validate_valor_total(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Valor total deve ser positivo.")
        return value

    def validate_numero_parcelas(self, value):
        if value is not None:
            if value < 1:
                raise serializers.ValidationError("Numero de parcelas deve ser ao menos 1.")
            if value > 120:
                raise serializers.ValidationError("Maximo de 120 parcelas.")
        return value

    def validate_quantity(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Quantidade deve ser positiva.")
        return value

    def validate_exchange_rate_to_base(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Taxa de câmbio deve ser positiva.")
        return value

    def validate(self, data):
        if data.get("is_recorrente") and not data.get("recorrencia_tipo"):
            # Check if the instance already has it
            if self.instance and not self.instance.recorrencia_tipo:
                raise serializers.ValidationError({
                    "recorrencia_tipo": "Tipo de recorrencia e obrigatorio para lancamentos recorrentes."
                })
        return data


# =============================================================================
# PaymentTransaction (PIX)
# =============================================================================


class PaymentTransactionListSerializer(serializers.ModelSerializer):
    """List serializer — excludes payer_document for security."""

    invoice_number = serializers.SerializerMethodField()
    lancamento_descricao = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "transaction_type",
            "status",
            "amount",
            "currency",
            "pix_txid",
            "pix_e2e_id",
            "gateway_reference",
            "paid_at",
            "expires_at",
            "payer_name",
            "metadata_json",
            "invoice",
            "invoice_number",
            "lancamento",
            "lancamento_descricao",
            "contact",
            "contact_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields  # list is read-only

    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number if obj.invoice else None

    def get_lancamento_descricao(self, obj):
        return obj.lancamento.descricao if obj.lancamento else None

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}".strip()
        return None


class PaymentTransactionDetailSerializer(PaymentTransactionListSerializer):
    """Detail serializer — includes decrypted payer_document for authorized users."""

    payer_document = serializers.CharField(read_only=True)

    class Meta(PaymentTransactionListSerializer.Meta):
        fields = PaymentTransactionListSerializer.Meta.fields + ["payer_document"]


class PaymentTransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            "transaction_type",
            "amount",
            "currency",
            "pix_txid",
            "gateway_reference",
            "expires_at",
            "payer_name",
            "metadata_json",
            "invoice",
            "lancamento",
            "contact",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Valor deve ser positivo.")
        return value


# =============================================================================
# PIX Generate
# =============================================================================


class PixGenerateSerializer(serializers.Serializer):
    """Validates input for PIX QR Code generation."""

    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False, default="")
    expiration_minutes = serializers.IntegerField(required=False, default=30)
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    lancamento_id = serializers.UUIDField(required=False, allow_null=True)
    contact_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Valor deve ser positivo.")
        return value

    def validate_expiration_minutes(self, value):
        if value < 1 or value > 1440:
            raise serializers.ValidationError(
                "Tempo de expiração deve ser entre 1 e 1440 minutos."
            )
        return value
