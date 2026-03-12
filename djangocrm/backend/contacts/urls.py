from django.urls import path

from contacts import views
from conversations.views import ContactConversationsView

app_name = "api_contacts"

urlpatterns = [
    path("", views.ContactsListView.as_view()),
    path("search/", views.ContactSearchView.as_view()),
    path("<uuid:contact_id>/conversations/", ContactConversationsView.as_view(), name="contact-conversations"),
    path("<str:pk>/context/", views.ContactContextView.as_view(), name="contact-context"),
    path("<str:pk>/", views.ContactDetailView.as_view()),
    path("comment/<str:pk>/", views.ContactCommentView.as_view()),
    path("attachment/<str:pk>/", views.ContactAttachmentView.as_view()),
]
