"""
URL configuration for the automations app.

Endpoints:
    /api/automations/                   — List / Create automations
    /api/automations/<id>/              — Detail / Update / Delete
    /api/automations/<id>/logs/         — Execution logs
"""

from django.urls import path

from automations.views import (
    AutomationDetailView,
    AutomationListCreateView,
    AutomationLogListView,
)

app_name = "api_automations"

urlpatterns = [
    path("", AutomationListCreateView.as_view(), name="automation-list"),
    path("<uuid:pk>/", AutomationDetailView.as_view(), name="automation-detail"),
    path("<uuid:pk>/logs/", AutomationLogListView.as_view(), name="automation-logs"),
]
