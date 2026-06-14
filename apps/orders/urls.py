"""
Orders app URL routing.

Routes:
    POST /api/orders/                       - Create a new order
    GET  /api/orders/stores/{id}/orders/    - List orders for a store
"""

from django.urls import path

from .views import OrderCreateView, StoreOrderListView

urlpatterns = [
    path("", OrderCreateView.as_view(), name="order-create"),
    path("stores/<int:store_id>/orders/", StoreOrderListView.as_view(), name="store-order-list"),
]
