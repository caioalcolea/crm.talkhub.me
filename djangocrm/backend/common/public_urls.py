"""
Public URL aggregator — no authentication required.
Mounts at /api/public/ in crm/urls.py
"""

from django.urls import include, path

from common.views.contact_views import ContactFormSubmitView

app_name = "public"

urlpatterns = [
    # Contact form
    path("contact/", ContactFormSubmitView.as_view(), name="contact_form"),
    # Invoice / Estimate public portal
    path("", include("invoices.public_urls")),
]
