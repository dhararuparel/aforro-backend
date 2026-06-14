"""
Search filter definitions using django-filter.

Provides category, price range, store, and in-stock filters
for the product search endpoint.
"""

import django_filters
from django.db.models import QuerySet

from apps.products.models import Product


class ProductSearchFilter(django_filters.FilterSet):
    """
    Filter set for the product search endpoint.

    Filters:
        category    - filter by category ID
        min_price   - products priced >= min_price
        max_price   - products priced <= max_price
        store_id    - filter to products available in a given store
        in_stock    - if True, only return products with quantity > 0
                      (requires store_id to be meaningful)
    """

    category = django_filters.NumberFilter(field_name="category__id")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    store_id = django_filters.NumberFilter(method="filter_by_store")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["category", "min_price", "max_price", "store_id", "in_stock"]

    def filter_by_store(self, queryset: QuerySet, name: str, value: int) -> QuerySet:
        """Filter products that have an inventory record in the given store."""
        return queryset.filter(inventory_items__store_id=value)

    def filter_in_stock(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:
        """
        Filter products that are in stock.

        Requires store_id to be set — if no store is provided,
        'in_stock' filters across ALL stores (products with any inventory > 0).
        """
        if value:
            store_id = self.request.query_params.get("store_id")
            if store_id:
                return queryset.filter(
                    inventory_items__store_id=store_id,
                    inventory_items__quantity__gt=0,
                )
            return queryset.filter(inventory_items__quantity__gt=0)
        return queryset
