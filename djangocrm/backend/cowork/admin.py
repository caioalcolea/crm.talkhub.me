from django.contrib import admin

from cowork.models import CoworkInvite, CoworkRoom


@admin.register(CoworkRoom)
class CoworkRoomAdmin(admin.ModelAdmin):
    list_display = ["name", "org", "map_id", "is_active", "max_participants", "created_at"]
    list_filter = ["is_active", "map_id"]
    search_fields = ["name"]


@admin.register(CoworkInvite)
class CoworkInviteAdmin(admin.ModelAdmin):
    list_display = ["guest_name", "room", "org", "is_active", "use_count", "max_uses", "expires_at"]
    list_filter = ["is_active"]
    search_fields = ["guest_name", "guest_email", "token"]
    readonly_fields = ["token"]
