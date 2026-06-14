"""Stores app URL routing."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.orders.views import StoreOrderListView
from .views import StoreViewSet

router = DefaultRouter()
router.register("", StoreViewSet, basename="store")

urlpatterns = [
    path("<int:store_id>/orders/", StoreOrderListView.as_view(), name="store-order-list"),
    path("", include(router.urls)),
]

