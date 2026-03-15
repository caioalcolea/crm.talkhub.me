from django.urls import path

from contacts import views
from conversations.views import ContactConversationsView

app_name = "api_contacts"

urlpatterns = [
    path("", views.ContactsListView.as_view()),
    path("search/", views.ContactSearchView.as_view()),
    path("merge/", views.ContactMergeView.as_view(), name="contact-merge"),
    path("merge/preview/", views.ContactMergePreviewView.as_view(), name="contact-merge-preview"),
    path("<uuid:contact_id>/conversations/", ContactConversationsView.as_view(), name="contact-conversations"),
    # Extra contact info (emails, phones, addresses)
    path("<uuid:contact_id>/emails/", views.ContactExtraEmailView.as_view(), name="contact-extra-emails"),
    path("<uuid:contact_id>/emails/<uuid:pk>/", views.ContactExtraEmailView.as_view(), name="contact-extra-email-delete"),
    path("<uuid:contact_id>/phones/", views.ContactExtraPhoneView.as_view(), name="contact-extra-phones"),
    path("<uuid:contact_id>/phones/<uuid:pk>/", views.ContactExtraPhoneView.as_view(), name="contact-extra-phone-delete"),
    path("<uuid:contact_id>/addresses/", views.ContactExtraAddressView.as_view(), name="contact-extra-addresses"),
    path("<uuid:contact_id>/addresses/<uuid:pk>/", views.ContactExtraAddressView.as_view(), name="contact-extra-address-delete"),
    path("<str:pk>/context/", views.ContactContextView.as_view(), name="contact-context"),
    path("<str:pk>/duplicates/", views.ContactDuplicatesView.as_view(), name="contact-duplicates"),
    path("<str:pk>/", views.ContactDetailView.as_view()),
    path("comment/<str:pk>/", views.ContactCommentView.as_view()),
    path("attachment/<str:pk>/", views.ContactAttachmentView.as_view()),
]
