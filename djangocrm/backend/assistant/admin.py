from django.contrib import admin

from assistant.models import (
    AutopilotTemplate,
    ChannelDispatch,
    ReminderPolicy,
    ScheduledJob,
    TaskLink,
)


@admin.register(ReminderPolicy)
class ReminderPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "module_key",
        "trigger_type",
        "is_active",
        "next_run_at",
        "run_count",
        "org",
    ]
    list_filter = ["module_key", "trigger_type", "is_active", "org"]
    search_fields = ["name", "description"]
    readonly_fields = ["next_run_at", "last_run_at", "run_count", "error_count"]


@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = ["job_type", "status", "due_at", "attempt_count", "org"]
    list_filter = ["job_type", "status", "org"]
    readonly_fields = ["idempotency_key"]


@admin.register(ChannelDispatch)
class ChannelDispatchAdmin(admin.ModelAdmin):
    list_display = ["channel_type", "destination", "status", "sent_at", "org"]
    list_filter = ["channel_type", "status"]


@admin.register(TaskLink)
class TaskLinkAdmin(admin.ModelAdmin):
    list_display = ["task", "sync_mode", "status", "org"]
    list_filter = ["sync_mode", "status"]


@admin.register(AutopilotTemplate)
class AutopilotTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "module_key", "template_type", "is_system"]
    list_filter = ["category", "template_type", "is_system"]
