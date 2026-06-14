"""
Product serializers for validation and representation.

Serializers are kept thin — they only handle
I/O shape and validation. Business logic lives in services.
"""

from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""

    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    """
    Full product representation including nested category.

    Used in inventory listing and product detail endpoints.
    """

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        write_only=True,
        source="category",
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "price",
            "category",
            "category_id",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product lists.

    Returns only essential fields to reduce payload size.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "price", "category_name", "created_at"]
