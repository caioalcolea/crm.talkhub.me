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
"""

from django.urls import path

from conversations.views import (
    ConversationAssignView,
    ConversationBotView,
    ConversationDetailView,
    ConversationListView,
    MessageCreateView,
    MessageListView,
)

app_name = "api_conversations"

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversation-list"),
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
