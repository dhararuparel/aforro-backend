"""
API URL routing - all /api/ endpoints are registered here.

URL structure:
    /api/products/                  - product CRUD
    /api/products/categories/       - category CRUD
    /api/stores/                    - store listing
    /api/stores/{id}/inventory/     - store inventory (via StoreViewSet action)
    /api/stores/{id}/orders/        - store order list (via orders app)
    /api/orders/                    - create order
    /api/search/products/           - product search
    /api/search/suggest/            - autocomplete
"""

from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.authentication.urls")),
    path("collections/", include("apps.collections.urls")),
    path("documents/", include("apps.documents.urls")),
]
