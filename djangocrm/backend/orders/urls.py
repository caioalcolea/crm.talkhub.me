from django.urls import path

from orders import views

app_name = "api_orders"

urlpatterns = [
    path("", views.OrderListView.as_view(), name="order_list"),
    path("<uuid:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("<uuid:pk>/activate/", views.OrderActivateView.as_view(), name="order_activate"),
    path(
        "<uuid:order_id>/line-items/",
        views.OrderLineItemListView.as_view(),
        name="order_line_items",
    ),
    path(
        "<uuid:order_id>/line-items/<uuid:pk>/",
        views.OrderLineItemDetailView.as_view(),
        name="order_line_item_detail",
    ),
]
