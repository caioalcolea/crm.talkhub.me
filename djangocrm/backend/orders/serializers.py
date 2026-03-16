from rest_framework import serializers

from orders.models import Order, OrderLineItem


class OrderLineItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, default="")

    class Meta:
        model = OrderLineItem
        fields = (
            "id",
            "product",
            "product_name",
            "name",
            "description",
            "quantity",
            "unit_price",
            "discount_amount",
            "total",
            "sort_order",
        )
        read_only_fields = ("id", "total")


class OrderListSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True, default="")
    contact_name = serializers.SerializerMethodField()
    line_items_count = serializers.IntegerField(source="line_items.count", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "name",
            "order_number",
            "order_type",
            "status",
            "account",
            "account_name",
            "contact",
            "contact_name",
            "currency",
            "total_amount",
            "order_date",
            "line_items_count",
            "created_at",
        )

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name or ''} {obj.contact.last_name or ''}".strip()
        return ""


class OrderSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True, default="")
    contact_name = serializers.SerializerMethodField()
    line_items = OrderLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "name",
            "order_number",
            "order_type",
            "status",
            "account",
            "account_name",
            "contact",
            "contact_name",
            "opportunity",
            "currency",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "order_date",
            "activated_date",
            "shipped_date",
            "billing_address_line",
            "billing_city",
            "billing_state",
            "billing_postcode",
            "billing_country",
            "shipping_address_line",
            "shipping_city",
            "shipping_state",
            "shipping_postcode",
            "shipping_country",
            "description",
            "line_items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_contact_name(self, obj):
        if obj.contact:
            return f"{obj.contact.first_name or ''} {obj.contact.last_name or ''}".strip()
        return ""


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "name",
            "order_number",
            "order_type",
            "status",
            "account",
            "contact",
            "opportunity",
            "currency",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "order_date",
            "description",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "profile"):
            validated_data["org"] = request.profile.org
        return super().create(validated_data)
