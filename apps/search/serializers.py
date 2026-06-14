"""
Search result serializers.
"""

from rest_framework import serializers

from apps.products.models import Product


class ProductSearchResultSerializer(serializers.ModelSerializer):
    """
    Serializer for product search results.

    Includes optional inventory quantity when store_id is provided
    (populated via annotation in the view).
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    category_id = serializers.IntegerField(source="category.id", read_only=True)

    # Optional field — populated via annotation when store_id is given
    inventory_quantity = serializers.IntegerField(
        read_only=True,
        default=None,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "price",
            "category_id",
            "category_name",
            "created_at",
            "inventory_quantity",
        ]


class AutocompleteResultSerializer(serializers.Serializer):
    """
    Serializer for autocomplete suggestions.

    Returns a flat list of title/category pairs for fast rendering.
    """

    id = serializers.IntegerField()
    title = serializers.CharField()
    category = serializers.CharField(source="category__name")
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
