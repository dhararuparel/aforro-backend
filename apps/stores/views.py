"""
Store and Inventory API views.

GET /api/stores/                    - list stores
GET /api/stores/{id}/               - store detail
GET /api/stores/{id}/inventory/     - store inventory (with caching)
"""

import logging

from django.core.cache import cache
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.exceptions import StoreNotFoundError

from .models import Inventory, Store
from .serializers import InventorySerializer, StoreSerializer

logger = logging.getLogger(__name__)

# Cache TTL: 5 minutes. Invalidated by signals on any inventory change.
INVENTORY_CACHE_TTL = 300


@extend_schema_view(
    list=extend_schema(tags=["Stores"], summary="List all stores"),
    retrieve=extend_schema(tags=["Stores"], summary="Get store detail"),
    inventory=extend_schema(
        tags=["Inventory"],
        summary="Get store inventory",
        description=(
            "Returns a paginated, alphabetically sorted list of inventory items "
            "for the specified store. Results are cached in Redis for 5 minutes "
            "and invalidated automatically on any inventory change."
        ),
    ),
)
class StoreViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Store read endpoints and nested inventory listing."""

    queryset = Store.objects.all().order_by("name")
    serializer_class = StoreSerializer

    @action(detail=True, methods=["get"], url_path="inventory")
    def inventory(self, request: Request, pk: str | None = None) -> Response:
        """
        List inventory for a specific store.

        Results are cached per store. Cache is invalidated automatically
        whenever an inventory item is saved or deleted via Django signals.

        Query params:
            page, page_size — standard pagination
        """
        store = self._get_store_or_404(pk)
        cache_key = f"inventory_store_{store.pk}"

        # ------------------------------------------------------------------
        # Cache strategy: store the full queryset result as a list of dicts.
        # We cache BEFORE pagination so that page-level requests still benefit
        # from the warm cache (Django REST paginates the pre-serialized list).
        # ------------------------------------------------------------------
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.debug("Inventory cache HIT for store %s", store.pk)
        else:
            logger.debug("Inventory cache MISS for store %s — querying DB", store.pk)
            qs = (
                Inventory.objects.filter(store=store)
                .select_related("product", "product__category")
                .order_by("product__title")  # alphabetical sort
            )
            serializer = InventorySerializer(qs, many=True)
            cached_data = serializer.data
            cache.set(cache_key, cached_data, INVENTORY_CACHE_TTL)

        # Apply DRF pagination to the (possibly cached) list
        page = self.paginate_queryset(cached_data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response({"success": True, "results": cached_data})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_store_or_404(self, pk: str | None) -> Store:
        """Retrieve a store by PK or raise a structured 404."""
        try:
            return Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            raise StoreNotFoundError()
