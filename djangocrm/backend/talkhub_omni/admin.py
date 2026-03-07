from django.contrib import admin

from .models import TalkHubConnection, TalkHubFieldMapping, TalkHubSyncJob


@admin.register(TalkHubConnection)
class TalkHubConnectionAdmin(admin.ModelAdmin):
    list_display = ("org", "workspace_name", "is_connected", "last_sync_at")
    list_filter = ("is_connected",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TalkHubSyncJob)
class TalkHubSyncJobAdmin(admin.ModelAdmin):
    list_display = ("org", "sync_type", "status", "total_records", "created_at")
    list_filter = ("status", "sync_type")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TalkHubFieldMapping)
class TalkHubFieldMappingAdmin(admin.ModelAdmin):
    list_display = ("org", "talkhub_field_name", "crm_field_key", "field_type")
    list_filter = ("field_type",)
