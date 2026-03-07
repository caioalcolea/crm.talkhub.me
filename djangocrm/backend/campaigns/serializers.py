"""
Serializers do app campaigns.

- CampaignSerializer: Leitura de campanhas.
- CampaignWriteSerializer: Criação/atualização de campanhas.
- CampaignAudienceSerializer: Leitura de audiências.
- CampaignAudienceWriteSerializer: Criação/atualização de audiências.
- CampaignRecipientSerializer: Leitura de destinatários.
- CampaignStepSerializer: Leitura de etapas.
- CampaignStepWriteSerializer: Criação/atualização de etapas.
"""

from rest_framework import serializers

from campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignRecipient,
    CampaignStep,
)


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer de leitura para Campaign."""

    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "campaign_type",
            "status",
            "subject",
            "body_template",
            "scheduled_at",
            "started_at",
            "completed_at",
            "total_recipients",
            "sent_count",
            "delivered_count",
            "opened_count",
            "clicked_count",
            "failed_count",
            "bounce_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CampaignWriteSerializer(serializers.ModelSerializer):
    """Serializer de escrita para Campaign."""

    class Meta:
        model = Campaign
        fields = (
            "name",
            "campaign_type",
            "status",
            "subject",
            "body_template",
            "scheduled_at",
        )

    def validate_campaign_type(self, value):
        valid = [c[0] for c in Campaign.TYPE_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f"Tipo inválido. Opções: {', '.join(valid)}"
            )
        return value

    def validate_status(self, value):
        valid = [c[0] for c in Campaign.STATUS_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f"Status inválido. Opções: {', '.join(valid)}"
            )
        return value

    def validate(self, attrs):
        status = attrs.get("status")
        campaign_type = attrs.get(
            "campaign_type",
            getattr(self.instance, "campaign_type", None) if self.instance else None,
        )
        # Require subject for email_blast
        if campaign_type == "email_blast" and status == "scheduled":
            subject = attrs.get(
                "subject",
                getattr(self.instance, "subject", None) if self.instance else None,
            )
            if not subject:
                raise serializers.ValidationError(
                    {"subject": "Assunto é obrigatório para Email Blast."}
                )
        return attrs


class CampaignAudienceSerializer(serializers.ModelSerializer):
    """Serializer de leitura para CampaignAudience."""

    class Meta:
        model = CampaignAudience
        fields = (
            "id",
            "campaign",
            "name",
            "filter_criteria",
            "contact_count",
            "created_at",
        )
        read_only_fields = fields


class CampaignAudienceWriteSerializer(serializers.ModelSerializer):
    """Serializer de escrita para CampaignAudience."""

    class Meta:
        model = CampaignAudience
        fields = ("name", "filter_criteria")


class CampaignRecipientSerializer(serializers.ModelSerializer):
    """Serializer de leitura para CampaignRecipient."""

    contact_name = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()

    class Meta:
        model = CampaignRecipient
        fields = (
            "id",
            "campaign",
            "contact",
            "contact_name",
            "contact_email",
            "status",
            "sent_at",
            "delivered_at",
            "opened_at",
            "clicked_at",
            "error_detail",
            "current_step",
            "created_at",
        )
        read_only_fields = fields

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name} {obj.contact.last_name}".strip()
        return ""

    def get_contact_email(self, obj):
        if obj.contact:
            return obj.contact.email or ""
        return ""


class CampaignStepSerializer(serializers.ModelSerializer):
    """Serializer de leitura para CampaignStep."""

    class Meta:
        model = CampaignStep
        fields = (
            "id",
            "campaign",
            "step_order",
            "channel",
            "subject",
            "body_template",
            "delay_hours",
            "sent_count",
            "created_at",
        )
        read_only_fields = fields


class CampaignStepWriteSerializer(serializers.ModelSerializer):
    """Serializer de escrita para CampaignStep."""

    class Meta:
        model = CampaignStep
        fields = ("step_order", "channel", "subject", "body_template", "delay_hours")

    def validate_channel(self, value):
        valid = [c[0] for c in CampaignStep.CHANNEL_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f"Canal inválido. Opções: {', '.join(valid)}"
            )
        return value
