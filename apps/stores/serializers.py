"""
Store and Inventory serializers.
"""

from rest_framework import serializers

from .models import Inventory, Store


class StoreSerializer(serializers.ModelSerializer):
    """Full store representation."""

    class Meta:
        model = Store
        fields = ["id", "name", "location"]


class InventorySerializer(serializers.ModelSerializer):
    """
    Inventory listing serializer.

    Returns product details alongside quantity for the
    GET /api/stores/{id}/inventory/ endpoint.
    """

    product_title = serializers.CharField(source="product.title", read_only=True)
    category = serializers.CharField(source="product.category.name", read_only=True)
    price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Inventory
        fields = ["id", "product_title", "category", "price", "quantity"]


class InventoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating inventory items."""

    class Meta:
        model = Inventory
        fields = ["store", "product", "quantity"]

    def validate_quantity(self, value: int) -> int:
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value
