"""
Search and autocomplete API views.

GET /api/search/products/   - full product search with filters and sorting
GET /api/search/suggest/    - autocomplete suggestions
"""

import logging

from django.db.models import Case, IntegerField, OuterRef, Subquery, Value, When, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.stores.models import Inventory
from apps.common.pagination import CustomPageNumberPagination

from .filters import ProductSearchFilter
from .serializers import AutocompleteResultSerializer, ProductSearchResultSerializer

logger = logging.getLogger(__name__)

# Minimum query length for autocomplete
AUTOCOMPLETE_MIN_LENGTH = 3
AUTOCOMPLETE_MAX_RESULTS = 10


class ProductSearchView(APIView):
    """
    GET /api/search/products/

    Full-text product search with filters, sorting, and pagination.

    Query parameters:
        q           - free-text search against title, description, category
        category    - filter by category ID
        min_price   - minimum price filter
        max_price   - maximum price filter
        store_id    - filter to store inventory; includes quantity in results
        in_stock    - boolean; only return in-stock products
        sort        - one of: price_asc, price_desc, newest, relevance (default)
        page        - page number
        page_size   - results per page (max 100)

    Relevance ranking (sort=relevance):
        Products whose title starts with the query score highest (rank=1),
        then title contains (rank=2), then description contains (rank=3),
        then category name (rank=4). Implemented via Case/When annotation.
    """

    pagination_class = CustomPageNumberPagination

    @extend_schema(
        tags=["Search"],
        summary="Search products",
        parameters=[
            OpenApiParameter("q", str, description="Search query"),
            OpenApiParameter("category", int, description="Category ID filter"),
            OpenApiParameter("min_price", float, description="Minimum price"),
            OpenApiParameter("max_price", float, description="Maximum price"),
            OpenApiParameter("store_id", int, description="Filter by store; includes inventory quantity"),
            OpenApiParameter("in_stock", bool, description="Only return in-stock products"),
            OpenApiParameter(
                "sort",
                str,
                enum=["relevance", "price_asc", "price_desc", "newest"],
                description="Sort order",
            ),
        ],
        responses={200: ProductSearchResultSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Search products with optional filters and sorting."""
        query = request.query_params.get("q", "").strip()
        sort = request.query_params.get("sort", "relevance")
        store_id = request.query_params.get("store_id")

        # Build base queryset with eager-loaded relations
        qs = Product.objects.select_related("category")

        # Apply free-text search
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
            )

        # Apply django-filter filters (category, price, store, in_stock)
        filterset = ProductSearchFilter(request.query_params, queryset=qs, request=request)
        if not filterset.is_valid():
            return Response({"success": False, "errors": filterset.errors}, status=400)
        qs = filterset.qs

        # Annotate inventory quantity if store_id is provided
        if store_id:
            inventory_subquery = Subquery(
                Inventory.objects.filter(
                    product=OuterRef("pk"),
                    store_id=store_id,
                ).values("quantity")[:1]
            )
            qs = qs.annotate(inventory_quantity=inventory_subquery)
        else:
            qs = qs.annotate(inventory_quantity=Value(None, output_field=IntegerField()))

        # Sorting
        qs = cls_sort(qs, sort, query)

        # Deduplicate (joins from filter can cause duplicates)
        qs = qs.distinct()

        # Paginate and return
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = ProductSearchResultSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ProductSearchResultSerializer(qs, many=True)
        return Response({"success": True, "results": serializer.data})


def cls_sort(qs, sort: str, query: str):
    """
    Apply sort order to the queryset.

    Relevance ranking uses Case/When annotations to assign a numeric
    score based on WHERE the query term appears, then sorts by that score.
    """
    if sort == "price_asc":
        return qs.order_by("price")
    elif sort == "price_desc":
        return qs.order_by("-price")
    elif sort == "newest":
        return qs.order_by("-created_at")
    else:
        # Default: relevance ranking
        if query:
            qs = qs.annotate(
                relevance_rank=Case(
                    # Highest: title starts with the query
                    When(title__istartswith=query, then=Value(1)),
                    # Title contains the query
                    When(title__icontains=query, then=Value(2)),
                    # Description contains the query
                    When(description__icontains=query, then=Value(3)),
                    # Category name matches
                    When(category__name__icontains=query, then=Value(4)),
                    # Everything else
                    default=Value(5),
                    output_field=IntegerField(),
                )
            ).order_by("relevance_rank", "-created_at")
        else:
            qs = qs.order_by("-created_at")
        return qs


class AutocompleteView(APIView):
    """
    GET /api/search/suggest/?q=abc

    Returns up to 10 autocomplete suggestions for product titles.

    Query strategy:
        1. Prefix matches (title starts with query) — highest priority
        2. Contains matches (title contains query but doesn't start with it)
        3. Both sets are combined and limited to AUTOCOMPLETE_MAX_RESULTS

    Constraints:
        - Minimum query length: 3 characters
        - Maximum results: 10
        - Only matches on title field for performance
    """

    @extend_schema(
        tags=["Search"],
        summary="Autocomplete product suggestions",
        parameters=[
            OpenApiParameter(
                "q",
                str,
                required=True,
                description=f"Search prefix (minimum {AUTOCOMPLETE_MIN_LENGTH} characters)",
            )
        ],
        responses={
            200: AutocompleteResultSerializer(many=True),
            400: {"description": "Query too short"},
        },
    )
    def get(self, request: Request) -> Response:
        """Return autocomplete suggestions for the given query prefix."""
        query = request.query_params.get("q", "").strip()

        if len(query) < AUTOCOMPLETE_MIN_LENGTH:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "query_too_short",
                        "message": f"Query must be at least {AUTOCOMPLETE_MIN_LENGTH} characters.",
                    },
                },
                status=400,
            )

        fields = ["id", "title", "category__name", "price"]

        # Pass 1: Prefix matches (highest priority)
        prefix_qs = (
            Product.objects.filter(title__istartswith=query)
            .select_related("category")
            .values("id", "title", "category__name", "price")
            .order_by("title")[: AUTOCOMPLETE_MAX_RESULTS]
        )
        prefix_results = list(prefix_qs)
        prefix_ids = {r["id"] for r in prefix_results}

        # Pass 2: Contains matches (fill remaining slots)
        remaining = AUTOCOMPLETE_MAX_RESULTS - len(prefix_results)
        contains_results = []
        if remaining > 0:
            contains_results = list(
                Product.objects.filter(title__icontains=query)
                .exclude(id__in=prefix_ids)
                .select_related("category")
                .values("id", "title", "category__name", "price")
                .order_by("title")[:remaining]
            )

        suggestions = prefix_results + contains_results

        return Response(
            {
                "success": True,
                "query": query,
                "count": len(suggestions),
                "suggestions": suggestions,
            }
        )
