"""
Serializers do app automations.

- AutomationSerializer: Leitura de automações.
- AutomationWriteSerializer: Criação/atualização de automações.
- AutomationLogSerializer: Leitura de logs de execução.
"""

from rest_framework import serializers

from automations.models import Automation, AutomationLog


class AutomationSerializer(serializers.ModelSerializer):
    """Serializer de leitura para Automation."""

    class Meta:
        model = Automation
        fields = (
            "id",
            "name",
            "automation_type",
            "is_active",
            "config_json",
            "last_run_at",
            "run_count",
            "error_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AutomationWriteSerializer(serializers.ModelSerializer):
    """Serializer de escrita para Automation."""

    class Meta:
        model = Automation
        fields = (
            "name",
            "automation_type",
            "is_active",
            "config_json",
        )

    def validate_automation_type(self, value):
        valid = [c[0] for c in Automation.TYPE_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f"Tipo inválido. Opções: {', '.join(valid)}"
            )
        return value

    def validate(self, attrs):
        """Validar config_json de acordo com o automation_type."""
        automation_type = attrs.get(
            "automation_type",
            getattr(self.instance, "automation_type", None) if self.instance else None,
        )
        config_json = attrs.get("config_json")

        if automation_type == "routine" and config_json:
            from automations.tasks import _validate_routine_config

            valid, error = _validate_routine_config(config_json)
            if not valid:
                raise serializers.ValidationError({"config_json": error})

        if automation_type == "logic_rule" and config_json:
            from automations.engine import validate_logic_rule_config

            valid, error = validate_logic_rule_config(config_json)
            if not valid:
                raise serializers.ValidationError({"config_json": error})

        if automation_type == "social" and config_json:
            from automations.engine import validate_social_config

            valid, error = validate_social_config(config_json)
            if not valid:
                raise serializers.ValidationError({"config_json": error})

        return attrs


class AutomationLogSerializer(serializers.ModelSerializer):
    """Serializer de leitura para AutomationLog."""

    class Meta:
        model = AutomationLog
        fields = (
            "id",
            "automation",
            "status",
            "trigger_data",
            "result_data",
            "error_detail",
            "execution_time_ms",
            "created_at",
        )
        read_only_fields = fields
