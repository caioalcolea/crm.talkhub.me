from django.urls import include, path

from conversations.views import ContactConversationsView
from tasks.urls import board_urlpatterns

app_name = "common_urls"
urlpatterns = [
    path("", include(("common.urls"))),
    path("accounts/", include("accounts.urls", namespace="api_accounts")),
    path("contacts/", include("contacts.urls", namespace="api_contacts")),
    path("leads/", include("leads.urls", namespace="api_leads")),
    path("opportunities/", include("opportunity.urls", namespace="api_opportunities")),
    # Teams URLs are now in common app at /api/teams/
    path("tasks/", include("tasks.urls", namespace="api_tasks")),
    path("cases/", include("cases.urls", namespace="api_cases")),
    path("invoices/", include("invoices.api_urls", namespace="api_invoices")),
    path(
        "boards/", include((board_urlpatterns, "api_boards"))
    ),  # Kanban Boards (merged into tasks app)
    path("talkhub/", include("talkhub_omni.urls", namespace="api_talkhub")),
    path("financeiro/", include("financeiro.api_urls", namespace="api_financeiro")),
    path("integrations/", include("integrations.urls", namespace="api_integrations")),
    path("channels/", include("channels.urls", namespace="api_channels")),
    path("conversations/", include("conversations.urls", namespace="api_conversations")),
    path("automations/", include("automations.urls", namespace="api_automations")),
    path("campaigns/", include("campaigns.urls", namespace="api_campaigns")),
    path(
        "contacts/<uuid:contact_id>/conversations/",
        ContactConversationsView.as_view(),
        name="contact-conversations",
    ),
]
