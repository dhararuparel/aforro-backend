"""
Root URL configuration for Aforro Backend.

URL routing is organized by app with versioned API prefix.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common.views import HealthCheckView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),

    # API v1
    path("api/", include("config.api_urls")),

    # Root paths for direct assignment compatibility
    path("orders/", include("apps.orders.urls")),
    path("stores/", include("apps.stores.urls")),

    # OpenAPI Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # ReDoc UI
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
