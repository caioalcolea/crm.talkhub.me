from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from assistant.models import (
    AutopilotTemplate,
    ChannelDispatch,
    ReminderPolicy,
    ScheduledJob,
    TaskLink,
)


class ReminderPolicySerializer(serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()
    target_display = serializers.SerializerMethodField()

    class Meta:
        model = ReminderPolicy
        fields = [
            "id",
            "name",
            "description",
            "target_content_type",
            "target_object_id",
            "target_type",
            "target_display",
            "module_key",
            "owner_user",
            "is_active",
            "trigger_type",
            "trigger_config",
            "channel_config",
            "task_config",
            "message_template",
            "approval_policy",
            "timezone",
            "next_run_at",
            "last_run_at",
            "run_count",
            "error_count",
            "metadata_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "next_run_at",
            "last_run_at",
            "run_count",
            "error_count",
            "created_at",
            "updated_at",
        ]

    def get_target_type(self, obj):
        if obj.target_content_type:
            return f"{obj.target_content_type.app_label}.{obj.target_content_type.model}"
        return None

    def get_target_display(self, obj):
        try:
            target = obj.target
            return str(target)[:100] if target else ""
        except Exception:
            return ""


class ReminderPolicyWriteSerializer(serializers.ModelSerializer):
    target_type = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = ReminderPolicy
        fields = [
            "name",
            "description",
            "target_type",
            "target_object_id",
            "module_key",
            "trigger_type",
            "trigger_config",
            "channel_config",
            "task_config",
            "message_template",
            "approval_policy",
            "timezone",
            "metadata_json",
        ]

    def validate_target_type(self, value):
        try:
            app_label, model = value.split(".")
            ct = ContentType.objects.get(app_label=app_label, model=model)
            return ct
        except (ValueError, ContentType.DoesNotExist):
            raise serializers.ValidationError(
                f"Invalid target_type '{value}'. Use format 'app_label.model'."
            )

    def validate_trigger_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("trigger_config must be a dict.")
        return value

    def validate(self, data):
        trigger_type = data.get("trigger_type")
        trigger_config = data.get("trigger_config", {})

        if trigger_type == "due_date":
            if not trigger_config.get("date_field"):
                raise serializers.ValidationError(
                    {"trigger_config": "due_date trigger requires 'date_field'."}
                )
        elif trigger_type == "recurring":
            if not trigger_config.get("interval_days"):
                raise serializers.ValidationError(
                    {"trigger_config": "recurring trigger requires 'interval_days'."}
                )
        elif trigger_type == "cron":
            if not trigger_config.get("cron_expression"):
                raise serializers.ValidationError(
                    {"trigger_config": "cron trigger requires 'cron_expression'."}
                )

        return data

    def create(self, validated_data):
        target_ct = validated_data.pop("target_type")
        validated_data["target_content_type"] = target_ct
        validated_data["org"] = self.context["request"].profile.org
        validated_data["owner_user"] = self.context["request"].profile
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "target_type" in validated_data:
            target_ct = validated_data.pop("target_type")
            validated_data["target_content_type"] = target_ct
        return super().update(instance, validated_data)


class ScheduledJobSerializer(serializers.ModelSerializer):
    source_type = serializers.SerializerMethodField()
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledJob
        fields = [
            "id",
            "job_type",
            "source_content_type",
            "source_object_id",
            "source_type",
            "target_content_type",
            "target_object_id",
            "target_type",
            "assigned_user",
            "due_at",
            "status",
            "attempt_count",
            "max_attempts",
            "last_error",
            "approval_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_source_type(self, obj):
        if obj.source_content_type:
            return f"{obj.source_content_type.app_label}.{obj.source_content_type.model}"
        return None

    def get_target_type(self, obj):
        if obj.target_content_type:
            return f"{obj.target_content_type.app_label}.{obj.target_content_type.model}"
        return None


class ChannelDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelDispatch
        fields = [
            "id",
            "scheduled_job",
            "channel_type",
            "provider_key",
            "destination",
            "message_payload",
            "status",
            "provider_message_id",
            "error_message",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class TaskLinkSerializer(serializers.ModelSerializer):
    source_type = serializers.SerializerMethodField()

    class Meta:
        model = TaskLink
        fields = [
            "id",
            "source_content_type",
            "source_object_id",
            "source_type",
            "task",
            "sync_mode",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def get_source_type(self, obj):
        if obj.source_content_type:
            return f"{obj.source_content_type.app_label}.{obj.source_content_type.model}"
        return None


class AutopilotTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutopilotTemplate
        fields = [
            "id",
            "name",
            "category",
            "module_key",
            "template_type",
            "config_template",
            "message_template",
            "is_system",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
