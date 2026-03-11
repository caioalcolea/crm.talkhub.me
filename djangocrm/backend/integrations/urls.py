"""
URL configuration for the integrations app.

Endpoints:
    /api/integrations/                              — List integrations
    /api/integrations/health/                       — Health dashboard (all active)
    /api/integrations/logs/                         — Integration logs
    /api/integrations/webhooks/logs/                — Webhook logs
    /api/integrations/webhooks/<slug>/              — Webhook receiver (AllowAny)
    /api/integrations/field-mappings/               — Field mappings CRUD
    /api/integrations/field-mappings/<id>/          — Field mapping detail
    /api/integrations/conflicts/                    — Conflict logs
    /api/integrations/flags/                        — Feature flags list
    /api/integrations/flags/<feature_key>/          — Feature flag toggle
    /api/integrations/<slug>/                       — Integration detail
    /api/integrations/<slug>/connect/               — Connect integration
    /api/integrations/<slug>/disconnect/            — Disconnect integration
    /api/integrations/<slug>/health/                — Health check (single)
    /api/integrations/<slug>/sync/                  — Trigger sync
    /api/integrations/<slug>/sync/<job_id>/         — Sync job status
"""

from django.urls import path

from integrations.views import (
    ConflictLogListView,
    FeatureFlagDetailView,
    FeatureFlagListView,
    FieldMappingDetailView,
    FieldMappingListView,
    IntegrationConnectView,
    IntegrationDetailView,
    IntegrationDisconnectView,
    IntegrationHealthDashboardView,
    IntegrationHealthView,
    IntegrationListView,
    IntegrationLogListView,
    IntegrationReviewView,
    IntegrationSyncView,
    SyncJobDetailView,
    VariableRegistryView,
    WebhookDLQView,
    WebhookLogListView,
    webhook_receiver,
)

app_name = "api_integrations"

urlpatterns = [
    # List integrations
    path("", IntegrationListView.as_view(), name="integration-list"),
    # Logs (before <slug> to avoid conflict)
    path("logs/", IntegrationLogListView.as_view(), name="integration-logs"),
    # Webhook logs
    path("webhooks/logs/", WebhookLogListView.as_view(), name="webhook-logs"),
    # Webhook Dead Letter Queue
    path("webhooks/dlq/", WebhookDLQView.as_view(), name="webhook-dlq"),
    # Webhook receiver — token-based (preferred, secure multi-tenant)
    path("webhooks/<str:connector_slug>/<str:webhook_token>/", webhook_receiver, name="webhook-receiver-token"),
    # Webhook receiver — legacy (backward compat, AllowAny)
    path("webhooks/<str:connector_slug>/", webhook_receiver, name="webhook-receiver"),
    # Field mappings
    path("field-mappings/", FieldMappingListView.as_view(), name="field-mapping-list"),
    path("field-mappings/<uuid:pk>/", FieldMappingDetailView.as_view(), name="field-mapping-detail"),
    # Conflict logs
    path("conflicts/", ConflictLogListView.as_view(), name="conflict-logs"),
    # Feature flags
    path("flags/", FeatureFlagListView.as_view(), name="feature-flag-list"),
    path("flags/<str:feature_key>/", FeatureFlagDetailView.as_view(), name="feature-flag-detail"),
    # Review agent
    path("review/", IntegrationReviewView.as_view(), name="integration-review"),
    # Variable registry
    path("variables/", VariableRegistryView.as_view(), name="variable-registry"),
    # Health dashboard (all integrations)
    path("health/", IntegrationHealthDashboardView.as_view(), name="integration-health-dashboard"),
    # Integration detail and actions (slug-based, must be last)
    path("<str:connector_slug>/", IntegrationDetailView.as_view(), name="integration-detail"),
    path("<str:connector_slug>/connect/", IntegrationConnectView.as_view(), name="integration-connect"),
    path("<str:connector_slug>/disconnect/", IntegrationDisconnectView.as_view(), name="integration-disconnect"),
    path("<str:connector_slug>/health/", IntegrationHealthView.as_view(), name="integration-health"),
    path("<str:connector_slug>/sync/", IntegrationSyncView.as_view(), name="integration-sync"),
    path("<str:connector_slug>/sync/<uuid:job_id>/", SyncJobDetailView.as_view(), name="sync-job-detail"),
]
