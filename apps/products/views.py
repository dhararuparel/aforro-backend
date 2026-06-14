"""
Product API views.

Views are intentionally thin — they delegate to serializers for
I/O and handle HTTP concerns only.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


@extend_schema_view(
    list=extend_schema(tags=["Products"], summary="List all products"),
    retrieve=extend_schema(tags=["Products"], summary="Get product detail"),
    create=extend_schema(tags=["Products"], summary="Create a product"),
)
class ProductViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read/create products.

    Use the search endpoint for filtered/sorted product discovery.
    """

    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category").order_by("-created_at")


@extend_schema_view(
    list=extend_schema(tags=["Products"], summary="List all categories"),
    retrieve=extend_schema(tags=["Products"], summary="Get category detail"),
    create=extend_schema(tags=["Products"], summary="Create a category"),
)
class CategoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Category management endpoints."""

    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by("name")
