from django.urls import path

from cowork.views import (
    CoworkAuthTokenView,
    CoworkInviteListCreateView,
    CoworkInviteRevokeView,
    CoworkRoomDetailView,
    CoworkRoomListCreateView,
)

app_name = "api_cowork"

urlpatterns = [
    path("rooms/", CoworkRoomListCreateView.as_view(), name="room-list"),
    path("rooms/<uuid:pk>/", CoworkRoomDetailView.as_view(), name="room-detail"),
    path(
        "rooms/<uuid:room_id>/invites/",
        CoworkInviteListCreateView.as_view(),
        name="invite-list",
    ),
    path("invites/<uuid:pk>/", CoworkInviteRevokeView.as_view(), name="invite-revoke"),
    path("auth/token/", CoworkAuthTokenView.as_view(), name="auth-token"),
]
