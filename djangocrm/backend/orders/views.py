import logging

from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext
from orders.models import Order, OrderLineItem
from orders.serializers import (
    OrderCreateSerializer,
    OrderLineItemSerializer,
    OrderListSerializer,
    OrderSerializer,
)

logger = logging.getLogger(__name__)


class OrderListView(APIView, LimitOffsetPagination):
    """List and create orders"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(tags=["Orders"], operation_id="orders_list")
    def get(self, request):
        queryset = Order.objects.filter(org=request.profile.org)

        # Filter by order_type
        order_type = request.query_params.get("order_type")
        if order_type in ("sales", "purchase"):
            queryset = queryset.filter(order_type=order_type)

        # Filter by status
        order_status = request.query_params.get("status")
        if order_status:
            queryset = queryset.filter(status=order_status)

        # Search
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(order_number__icontains=search)
                | Q(account__name__icontains=search)
            )

        queryset = queryset.select_related("account", "contact").order_by("-created_at")
        results = self.paginate_queryset(queryset, request, view=self)

        return Response({
            "count": self.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": OrderListSerializer(results, many=True).data,
        })

    @extend_schema(tags=["Orders"], operation_id="orders_create")
    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            order = serializer.save()
            return Response(
                {
                    "error": False,
                    "message": "Order created",
                    "order": OrderSerializer(order).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class OrderDetailView(APIView):
    """Retrieve, update, and delete an order"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get_object(self, pk):
        return Order.objects.filter(
            id=pk, org=self.request.profile.org
        ).select_related("account", "contact").first()

    @extend_schema(tags=["Orders"], operation_id="orders_retrieve")
    def get(self, request, pk):
        order = self.get_object(pk)
        if not order:
            return Response(
                {"error": True, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrderSerializer(order).data)

    @extend_schema(tags=["Orders"], operation_id="orders_update")
    def put(self, request, pk):
        order = self.get_object(pk)
        if not order:
            return Response(
                {"error": True, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrderCreateSerializer(
            order, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            order = serializer.save()
            return Response({
                "error": False,
                "message": "Order updated",
                "order": OrderSerializer(order).data,
            })
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(tags=["Orders"], operation_id="orders_delete")
    def delete(self, request, pk):
        order = self.get_object(pk)
        if not order:
            return Response(
                {"error": True, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        order.delete()
        return Response(
            {"error": False, "message": "Order deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )


class OrderActivateView(APIView):
    """Activate a draft order — triggers Financeiro + Stock integration"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(tags=["Orders"], operation_id="orders_activate")
    def post(self, request, pk):
        order = Order.objects.filter(
            id=pk, org=request.profile.org
        ).first()
        if not order:
            return Response(
                {"error": True, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status != "DRAFT":
            return Response(
                {"error": True, "message": "Only draft orders can be activated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import datetime
        order.status = "ACTIVATED"
        order.activated_date = datetime.date.today()
        order.save(update_fields=["status", "activated_date"])

        # The post_save signal in orders/signals.py will handle Financeiro + Stock

        return Response({
            "error": False,
            "message": "Order activated",
            "order": OrderSerializer(order).data,
        })


class OrderLineItemListView(APIView):
    """List and create line items for an order"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, org=request.profile.org
        ).first()
        if not order:
            return Response(
                {"error": True, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        items = order.line_items.select_related("product").all()
        return Response(OrderLineItemSerializer(items, many=True).data)

    def post(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, org=request.profile.org
        ).first()
        if not order:
            return Response(
                {"error": True, "message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrderLineItemSerializer(data=request.data)
        if serializer.is_valid():
            item = serializer.save(order=order, org=order.org)

            # Recalculate order totals
            _recalculate_order_totals(order)

            return Response(
                OrderLineItemSerializer(item).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class OrderLineItemDetailView(APIView):
    """Update or delete an order line item"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def put(self, request, order_id, pk):
        item = OrderLineItem.objects.filter(
            id=pk, order_id=order_id, org=request.profile.org
        ).first()
        if not item:
            return Response(
                {"error": True, "message": "Line item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrderLineItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            _recalculate_order_totals(item.order)
            return Response(OrderLineItemSerializer(item).data)
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, order_id, pk):
        item = OrderLineItem.objects.filter(
            id=pk, order_id=order_id, org=request.profile.org
        ).first()
        if not item:
            return Response(
                {"error": True, "message": "Line item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        order = item.order
        item.delete()
        _recalculate_order_totals(order)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _recalculate_order_totals(order):
    """Recalculate order subtotal and total from line items."""
    from django.db.models import Sum
    totals = order.line_items.aggregate(
        subtotal=Sum("total"),
        discount=Sum("discount_amount"),
    )
    order.subtotal = totals["subtotal"] or 0
    order.total_amount = order.subtotal - order.discount_amount + order.tax_amount
    order.save(update_fields=["subtotal", "total_amount"])
