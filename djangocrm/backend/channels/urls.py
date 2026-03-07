"""
URL configuration for the channels app.

Endpoints:
    /api/channels/                          — List/create channels
    /api/channels/available/                — Available providers
    /api/channels/for-action/<action>/      — Channels for specific action
    /api/channels/<id>/                     — Channel detail (PATCH/DELETE)
    /api/channels/<id>/test/                — Test channel connection
"""

from django.urls import path

from channels.views import (
    ChannelAvailableView,
    ChannelConfigDetailView,
    ChannelConfigListView,
    ChannelForActionView,
    ChannelTestView,
)

app_name = "api_channels"

urlpatterns = [
    path("", ChannelConfigListView.as_view(), name="channel-list"),
    path("available/", ChannelAvailableView.as_view(), name="channel-available"),
    path("for-action/<str:action>/", ChannelForActionView.as_view(), name="channel-for-action"),
    path("<uuid:pk>/", ChannelConfigDetailView.as_view(), name="channel-detail"),
    path("<uuid:pk>/test/", ChannelTestView.as_view(), name="channel-test"),
]
