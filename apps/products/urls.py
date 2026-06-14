"""Products app URL routing."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register("", ProductViewSet, basename="product")

category_router = DefaultRouter()
category_router.register("", CategoryViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
    path("categories/", include(category_router.urls)),
]
