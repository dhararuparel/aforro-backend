"""
Order serializers for request validation and response representation.
"""

from rest_framework import serializers

from apps.products.models import Product

from .models import Order, OrderItem





class OrderItemInputSerializer(serializers.Serializer):
    """Validates a single line item in an order creation request."""

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        help_text="ID of the product to order.",
    )
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Number of units requested (must be >= 1).",
    )


class OrderCreateSerializer(serializers.Serializer):
    """
    Validates the full order creation payload.

    Example request body:
        {
            "store_id": 1,
            "items": [
                {"product_id": 42, "quantity": 3},
                {"product_id": 17, "quantity": 1}
            ]
        }
    """

    store_id = serializers.IntegerField(
        min_value=1,
        help_text="ID of the store to place the order against.",
    )
    items = serializers.ListField(
        child=OrderItemInputSerializer(),
        min_length=1,
        help_text="List of products and quantities to order.",
    )

    def validate_items(self, items: list) -> list:
        """Ensure no duplicate product_ids in a single order."""
        product_ids = [item["product_id"].pk for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Duplicate products in order. Combine quantities instead."
            )
        return items





class OrderItemOutputSerializer(serializers.ModelSerializer):
    """Represents a single order line item in the response."""

    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product_id", "product_title", "quantity_requested"]


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Full order representation including all items.

    Used as the response body for POST /api/orders/.
    """

    store_name = serializers.CharField(source="store.name", read_only=True)
    items = OrderItemOutputSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "store_name",
            "status",
            "created_at",
            "total_items",
            "items",
        ]

    def get_total_items(self, obj: Order) -> int:
        # Use annotated value if present, otherwise fall back to counting
        return getattr(obj, "total_items", obj.items.count())


class OrderListSerializer(serializers.ModelSerializer):
    """
    Compact order representation for list endpoints.

    GET /api/stores/{id}/orders/ uses this serializer.
    total_items is provided via a DB annotation (Count) to avoid N+1.
    """

    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "created_at", "total_items"]
