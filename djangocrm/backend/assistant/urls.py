from django.urls import path

from assistant.views import (
    AutopilotTemplateListView,
    EntityReminderListCreateView,
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
    # Templates
    path("templates/", AutopilotTemplateListView.as_view(), name="template_list"),
    # Entity reminders (generic)
    path(
        "reminders-for/<str:target_type>/<uuid:target_id>/",
        EntityReminderListCreateView.as_view(),
        name="entity_reminder_list_create",
    ),
]
