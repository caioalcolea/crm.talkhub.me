"""
URL configuration for the conversations app.

Endpoints:
    /api/conversations/                             — List conversations
    /api/conversations/<id>/                        — Conversation detail
    /api/conversations/<id>/messages/               — List/create messages
    /api/conversations/<id>/assign/                 — Assign agent
    /api/conversations/<id>/unassign/               — Unassign agent
    /api/conversations/<id>/bot/pause/              — Pause bot
    /api/conversations/<id>/bot/resume/             — Resume bot
    /api/conversations/<id>/delete/                 — Soft-delete
    /api/conversations/<id>/restore/                — Restore (admin)
    /api/conversations/<id>/permanent-delete/       — Permanent delete (admin)
"""

from django.urls import path

from conversations.views import (
    ConversationAssignView,
    ConversationBotView,
    ConversationDetailView,
    ConversationListView,
    ConversationPermanentDeleteView,
    ConversationSoftDeleteView,
    ConversationUpdatesView,
    MessageCreateView,
    MessageListView,
)

app_name = "api_conversations"

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversation-list"),
    path("updates/", ConversationUpdatesView.as_view(), name="conversation-updates"),
    path("<uuid:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path(
        "<uuid:conversation_id>/messages/",
        MessageListView.as_view(),
        name="message-list",
    ),
    path(
        "<uuid:conversation_id>/messages/create/",
        MessageCreateView.as_view(),
        name="message-create",
    ),
    # Soft-delete / restore / permanent delete (BEFORE generic <str:action> routes)
    path(
        "<uuid:pk>/delete/",
        ConversationSoftDeleteView.as_view(),
        {"action": "delete"},
        name="conversation-delete",
    ),
    path(
        "<uuid:pk>/restore/",
        ConversationSoftDeleteView.as_view(),
        {"action": "restore"},
        name="conversation-restore",
    ),
    path(
        "<uuid:pk>/permanent-delete/",
        ConversationPermanentDeleteView.as_view(),
        name="conversation-permanent-delete",
    ),
    # Generic action routes (assign/unassign) — AFTER specific routes
    path(
        "<uuid:pk>/<str:action>/",
        ConversationAssignView.as_view(),
        name="conversation-assign",
    ),
    path(
        "<uuid:pk>/bot/<str:action>/",
        ConversationBotView.as_view(),
        name="conversation-bot",
    ),
]
