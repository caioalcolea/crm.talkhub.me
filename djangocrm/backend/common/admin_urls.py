"""
Platform Administration URLs — Super Admin only.
All endpoints are prefixed with /api/admin-panel/
"""

from django.urls import path

from common.views.admin_views import (
    AdminDashboardView,
    AdminOrgDetailView,
    AdminOrgListView,
    AdminUserDetailView,
    AdminUserListView,
)

app_name = "admin_panel"

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin_dashboard"),
    path("orgs/", AdminOrgListView.as_view(), name="admin_org_list"),
    path("orgs/<uuid:pk>/", AdminOrgDetailView.as_view(), name="admin_org_detail"),
    path("users/", AdminUserListView.as_view(), name="admin_user_list"),
    path("users/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin_user_detail"),
]
