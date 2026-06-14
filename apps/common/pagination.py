"""
Custom pagination classes for Aforro Backend.

Provides a consistent, enriched pagination envelope with metadata.
"""

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom paginator that wraps results in a structured envelope:

        {
            "success": true,
            "pagination": {
                "count": 100,
                "total_pages": 5,
                "current_page": 1,
                "page_size": 20,
                "next": "http://...",
                "previous": null
            },
            "results": [...]
        }
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data: list[Any]) -> Response:
        return Response(
            {
                "success": True,
                "pagination": {
                    "count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "current_page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema: dict) -> dict:
        """DRF Spectacular schema for paginated responses."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "pagination": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "example": 100},
                        "total_pages": {"type": "integer", "example": 5},
                        "current_page": {"type": "integer", "example": 1},
                        "page_size": {"type": "integer", "example": 20},
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                    },
                },
                "results": schema,
            },
        }
