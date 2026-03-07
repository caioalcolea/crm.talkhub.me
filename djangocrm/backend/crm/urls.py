from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views
from django.urls import include, path
from django.urls import re_path as url
from django.views.generic import TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from common.views.invitation_views import InvitationAcceptView
from financeiro.pix_webhook import PixWebhookView
from campaigns.tracking import TrackingPixelView, UnsubscribeView

app_name = "crm"

urlpatterns = [
    url(
        r"^healthz/$",
        TemplateView.as_view(template_name="healthz.html"),
        name="healthz",
    ),
    # Public invitation accept (no JWT required)
    path("invite/accept/<uuid:token>/", InvitationAcceptView.as_view(), name="invitation_accept"),
    # Public PIX webhook (no JWT required)
    path("webhooks/pix/<slug:org_slug>/", PixWebhookView.as_view(), name="pix_webhook"),
    # Public campaign tracking (no JWT required)
    path("track/open/<uuid:recipient_id>/", TrackingPixelView.as_view(), name="tracking_pixel"),
    path("track/unsubscribe/<uuid:recipient_id>/", UnsubscribeView.as_view(), name="tracking_unsubscribe"),
    path("api/", include("common.app_urls", namespace="common_urls")),
    path("api/admin-panel/", include("common.admin_urls", namespace="admin_panel")),
    # Public portal endpoints (no auth required)
    path("api/public/", include("common.public_urls", namespace="public")),
    path(
        "logout/", views.LogoutView.as_view(), {"next_page": "/login/"}, name="logout"
    ),
    path("admin/", admin.site.urls),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # urlpatterns = urlpatterns + static(
    #     settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    # )
