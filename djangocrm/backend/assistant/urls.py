from django.urls import include, path
from rest_framework.routers import DefaultRouter

from assistant.views import (
    AIGenerateView,
    AssistantChatConfirmView,
    AssistantChatView,
    AssistantSessionDetailView,
    AssistantSessionListView,
    AutopilotTemplateViewSet,
    EntityReminderListCreateView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
    PresetsView,
    ReminderPolicyActivateView,
    ReminderPolicyDeactivateView,
    ReminderPolicyDetailView,
    ReminderPolicyListCreateView,
    RunsListView,
    ScheduledJobApproveView,
    ScheduledJobCancelView,
    ScheduledJobDetailView,
    ScheduledJobListView,
    ScheduledJobRetryView,
    TaskLinkListView,
)

app_name = "api_assistant"

router = DefaultRouter()
router.register("templates", AutopilotTemplateViewSet, basename="template")

urlpatterns = [
    # Reminder Policies
    path(
        "reminder-policies/",
        ReminderPolicyListCreateView.as_view(),
        name="reminder_policy_list",
    ),
    path(
        "reminder-policies/<uuid:pk>/",
        ReminderPolicyDetailView.as_view(),
        name="reminder_policy_detail",
    ),
    path(
        "reminder-policies/<uuid:pk>/activate/",
        ReminderPolicyActivateView.as_view(),
        name="reminder_policy_activate",
    ),
    path(
        "reminder-policies/<uuid:pk>/deactivate/",
        ReminderPolicyDeactivateView.as_view(),
        name="reminder_policy_deactivate",
    ),
    # Scheduled Jobs
    path(
        "scheduled-jobs/",
        ScheduledJobListView.as_view(),
        name="scheduled_job_list",
    ),
    path(
        "scheduled-jobs/<uuid:pk>/",
        ScheduledJobDetailView.as_view(),
        name="scheduled_job_detail",
    ),
    path(
        "scheduled-jobs/<uuid:pk>/retry/",
        ScheduledJobRetryView.as_view(),
        name="scheduled_job_retry",
    ),
    path(
        "scheduled-jobs/<uuid:pk>/cancel/",
        ScheduledJobCancelView.as_view(),
        name="scheduled_job_cancel",
    ),
    path(
        "scheduled-jobs/<uuid:pk>/approve/",
        ScheduledJobApproveView.as_view(),
        name="scheduled_job_approve",
    ),
    # Task Links
    path("task-links/", TaskLinkListView.as_view(), name="task_link_list"),
    # Consolidated runs
    path("runs/", RunsListView.as_view(), name="runs_list"),
    # Presets
    path("presets/", PresetsView.as_view(), name="presets"),
    # Router (templates CRUD)
    path("", include(router.urls)),
    # Entity reminders (generic)
    path(
        "reminders-for/<str:target_type>/<uuid:target_id>/",
        EntityReminderListCreateView.as_view(),
        name="entity_reminder_list_create",
    ),
    # AI copilot (legacy)
    path("ai/generate/", AIGenerateView.as_view(), name="ai_generate"),
    # ── Notifications ──
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notification_list",
    ),
    path(
        "notifications/unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notification_unread_count",
    ),
    path(
        "notifications/<uuid:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification_mark_read",
    ),
    path(
        "notifications/mark-all-read/",
        NotificationMarkAllReadView.as_view(),
        name="notification_mark_all_read",
    ),
    # ── Chat (Phase 1 — Conversational Assistant) ──
    path("chat/", AssistantChatView.as_view(), name="chat"),
    path("chat/confirm/", AssistantChatConfirmView.as_view(), name="chat_confirm"),
    path("sessions/", AssistantSessionListView.as_view(), name="session_list"),
    path(
        "sessions/<uuid:pk>/",
        AssistantSessionDetailView.as_view(),
        name="session_detail",
    ),
]
