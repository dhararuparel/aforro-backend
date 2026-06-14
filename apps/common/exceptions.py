"""
Custom exceptions and exception handler for Aforro Backend.

Provides structured, consistent error responses across all API endpoints.
"""

import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------


class AforroBaseException(APIException):
    """Base exception for all Aforro-specific API errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"


class InsufficientStockError(AforroBaseException):
    """Raised when a product does not have enough inventory to fulfill an order."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Insufficient stock for one or more products."
    default_code = "insufficient_stock"

    def __init__(self, product_title: str, available: int, requested: int) -> None:
        self.product_title = product_title
        self.available = available
        self.requested = requested
        detail = (
            f"Insufficient stock for '{product_title}': "
            f"requested {requested}, available {available}."
        )
        super().__init__(detail=detail)


class StoreNotFoundError(AforroBaseException):
    """Raised when a store is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Store not found."
    default_code = "store_not_found"


class OrderNotFoundError(AforroBaseException):
    """Raised when an order is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Order not found."
    default_code = "order_not_found"


class ProductNotFoundError(AforroBaseException):
    """Raised when a product is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Product not found."
    default_code = "product_not_found"


class InvalidOrderDataError(AforroBaseException):
    """Raised when order data fails business rule validation."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid order data."
    default_code = "invalid_order_data"


class InventoryNotFoundError(AforroBaseException):
    """Raised when an inventory record for a product/store is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Inventory record not found."
    default_code = "inventory_not_found"


# ---------------------------------------------------------------------------
# Custom exception handler
# ---------------------------------------------------------------------------


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom DRF exception handler that wraps all error responses in a
    consistent envelope structure:

        {
            "success": false,
            "error": {
                "code": "error_code",
                "message": "Human-readable message",
                "details": { ... }  // optional
            }
        }
    """
    # Convert Django ValidationError to DRF ValidationError first
    if isinstance(exc, DjangoValidationError):
        from rest_framework.exceptions import ValidationError

        exc = ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    # Let DRF handle the response object creation
    response = exception_handler(exc, context)

    if response is not None:
        # Log server errors
        if response.status_code >= 500:
            logger.error(
                "Server error: %s - %s",
                exc.__class__.__name__,
                str(exc),
                exc_info=True,
            )
        elif response.status_code >= 400:
            logger.warning(
                "Client error %s: %s - %s",
                response.status_code,
                exc.__class__.__name__,
                str(exc),
            )

        error_code = getattr(exc, "default_code", "error")
        if hasattr(exc, "get_codes"):
            codes = exc.get_codes()
            if isinstance(codes, str):
                error_code = codes
            elif isinstance(codes, dict):
                error_code = "validation_error"

        response.data = {
            "success": False,
            "error": {
                "code": error_code,
                "message": _get_error_message(response.data),
                "details": response.data if isinstance(response.data, dict) else None,
            },
        }

    return response


def _get_error_message(data: Any) -> str:
    """Extract a flat human-readable message from DRF error data."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return " ".join(str(item) for item in data)
    if isinstance(data, dict):
        # Try common keys first
        for key in ("detail", "non_field_errors", "message"):
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return str(val[0]) if val else ""
                return str(val)
        # Fall back to first value
        first = next(iter(data.values()), "")
        if isinstance(first, list):
            return str(first[0]) if first else ""
        return str(first)
    return str(data)
