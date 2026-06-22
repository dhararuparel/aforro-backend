"""
Common views shared across the application.
"""

import logging

from django.db import connection
from django.core.cache import cache
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint.

    Returns the health status of the application and its dependencies
    (database and Redis cache). Used by Docker health checks, load
    balancers, and monitoring systems.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Health"],
        summary="Service health check",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "database": {"type": "string"},
                    "cache": {"type": "string"},
                },
            }
        },
    )
    def get(self, request: Request) -> Response:
        """Check service health including database and cache connectivity."""
        health = {
            "status": "healthy",
            "database": "ok",
            "cache": "ok",
        }
        http_status = 200

        # Check database
        try:
            connection.ensure_connection()
        except Exception as e:
            logger.error("Health check - database error: %s", e)
            health["database"] = "error"
            health["status"] = "degraded"
            http_status = 503

        # Check Redis cache
        try:
            cache.set("health_check", "ok", timeout=5)
            result = cache.get("health_check")
            if result != "ok":
                raise ValueError("Cache read/write mismatch")
        except Exception as e:
            logger.error("Health check - cache error: %s", e)
            health["cache"] = "error"
            health["status"] = "degraded"
            http_status = 503

        return Response(health, status=http_status)


class IndexView(TemplateView):
    """
    Main landing page displaying links to OpenAPI documentation and endpoints.
    """
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["api_endpoints"] = [
            {
                "name": "Swagger UI",
                "url": "/api/docs/",
                "desc": "Explore and test the API endpoints interactively via Swagger.",
                "badge": "Interactive Docs"
            },
            {
                "name": "ReDoc",
                "url": "/api/redoc/",
                "desc": "Explore the structured OpenAPI schema using ReDoc.",
                "badge": "Reference Docs"
            },
            {
                "name": "API Root",
                "url": "/api/",
                "desc": "Check out the DRF API entry point.",
                "badge": "REST API"
            },
            {
                "name": "Health Status",
                "url": "/health/",
                "desc": "Verify database and cache connectivity.",
                "badge": "System status"
            }
        ]
        return context
