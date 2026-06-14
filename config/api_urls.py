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
    path("products/", include("apps.products.urls")),
    path("stores/", include("apps.stores.urls")),
    path("orders/", include("apps.orders.urls")),
    path("search/", include("apps.search.urls")),
]
