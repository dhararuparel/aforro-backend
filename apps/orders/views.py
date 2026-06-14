"""
Order API views.

POST /api/orders/               - create an order
GET  /api/stores/{id}/orders/   - list store orders (mounted in stores router)
"""

import logging

from django.db.models import Count
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import StoreNotFoundError
from apps.stores.models import Store

from .models import Order
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)
from .services import OrderService

logger = logging.getLogger(__name__)


class OrderCreateView(APIView):
    """
    POST /api/orders/

    Creates an order for a store using the OrderService.
    The view is intentionally thin — all business logic lives in the service.
    """

    @extend_schema(
        tags=["Orders"],
        summary="Create an order",
        description=(
            "Places an order against a store's inventory.\n\n"
            "- If all items are available: status=CONFIRMED, inventory deducted.\n"
            "- If any item is out of stock: status=REJECTED, no inventory change.\n"
            "- A Celery task is dispatched after confirmed orders."
        ),
        request=OrderCreateSerializer,
        responses={
            201: OrderDetailSerializer,
            200: OrderDetailSerializer,
            400: {"description": "Validation error"},
            404: {"description": "Store not found"},
        },
        examples=[
            OpenApiExample(
                "Confirmed Order Example",
                value={
                    "store_id": 1,
                    "items": [
                        {"product_id": 1, "quantity": 2},
                        {"product_id": 3, "quantity": 1},
                    ],
                },
                request_only=True,
            )
        ],
    )
    def post(self, request: Request) -> Response:
        """Process a new order request."""
        # Validate input
        input_serializer = OrderCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        validated = input_serializer.validated_data

        # Delegate to service layer
        result = OrderService.create_order(
            store_id=validated["store_id"],
            items=validated["items"],
        )

        # Serialize and return response
        output_serializer = OrderDetailSerializer(result.order)

        response_data = {
            "success": True,
            "message": result.message,
            "order": output_serializer.data,
        }

        if result.stock_issues:
            response_data["stock_issues"] = result.stock_issues

        # 201 for confirmed, 200 for rejected (no resource was fully created)
        http_status = (
            status.HTTP_201_CREATED
            if result.order.status == Order.Status.CONFIRMED
            else status.HTTP_200_OK
        )

        return Response(response_data, status=http_status)


class StoreOrderListView(APIView):
    """
    GET /api/stores/{store_id}/orders/

    Lists all orders for a specific store, sorted by newest first.
    Uses COUNT annotation to avoid N+1 on total_items.
    """

    @extend_schema(
        tags=["Orders"],
        summary="List store orders",
        description=(
            "Returns all orders for the given store, sorted newest first. "
            "total_items is computed with a DB-level COUNT annotation."
        ),
        responses={200: OrderListSerializer(many=True)},
    )
    def get(self, request: Request, store_id: int) -> Response:
        """Retrieve paginated order list for a store."""
        try:
            store = Store.objects.get(pk=store_id)
        except Store.DoesNotExist:
            raise StoreNotFoundError()

        orders = (
            Order.objects.filter(store=store)
            .annotate(total_items=Count("items"))
            .order_by("-created_at")
        )

        # Apply pagination
        from apps.common.pagination import CustomPageNumberPagination

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(orders, request)

        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = OrderListSerializer(orders, many=True)
        return Response({"success": True, "results": serializer.data})
