"""
URL configuration for the campaigns app.

Endpoints:
    /api/campaigns/                                     — List / Create
    /api/campaigns/<id>/                                — Detail / Update / Delete
    /api/campaigns/<id>/audiences/                      — List / Create audiences
    /api/campaigns/<id>/audience/preview/                — Preview audience count
    /api/campaigns/<id>/audience/generate/               — Generate recipients
    /api/campaigns/<id>/recipients/                      — List recipients
    /api/campaigns/<id>/steps/                           — List / Create steps
    /api/campaigns/<id>/steps/<step_id>/                 — Detail / Update / Delete step
    /api/campaigns/<id>/analytics/                       — Campaign analytics
    /api/campaigns/<id>/schedule/                        — Schedule campaign
    /api/campaigns/<id>/pause-resume/                    — Pause / Resume campaign
"""

from django.urls import path

from campaigns.views import (
    CampaignAnalyticsView,
    CampaignAudienceGenerateView,
    CampaignAudienceListCreateView,
    CampaignAudiencePreviewView,
    CampaignDetailView,
    CampaignListCreateView,
    CampaignPauseResumeView,
    CampaignRecipientListView,
    CampaignScheduleView,
    CampaignStepDetailView,
    CampaignStepListCreateView,
)

app_name = "api_campaigns"

urlpatterns = [
    path("", CampaignListCreateView.as_view(), name="campaign-list"),
    path("<uuid:pk>/", CampaignDetailView.as_view(), name="campaign-detail"),
    path("<uuid:campaign_id>/audiences/", CampaignAudienceListCreateView.as_view(), name="campaign-audiences"),
    path("<uuid:campaign_id>/audience/preview/", CampaignAudiencePreviewView.as_view(), name="campaign-audience-preview"),
    path("<uuid:campaign_id>/audience/generate/", CampaignAudienceGenerateView.as_view(), name="campaign-audience-generate"),
    path("<uuid:campaign_id>/recipients/", CampaignRecipientListView.as_view(), name="campaign-recipients"),
    path("<uuid:campaign_id>/steps/", CampaignStepListCreateView.as_view(), name="campaign-steps"),
    path("<uuid:campaign_id>/steps/<uuid:step_id>/", CampaignStepDetailView.as_view(), name="campaign-step-detail"),
    path("<uuid:campaign_id>/analytics/", CampaignAnalyticsView.as_view(), name="campaign-analytics"),
    path("<uuid:campaign_id>/schedule/", CampaignScheduleView.as_view(), name="campaign-schedule"),
    path("<uuid:campaign_id>/pause-resume/", CampaignPauseResumeView.as_view(), name="campaign-pause-resume"),
]
