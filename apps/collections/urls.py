from rest_framework.routers import DefaultRouter

from apps.collections.views import CollectionViewSet

app_name = "collections"

router = DefaultRouter()
router.register("", CollectionViewSet, basename="collection")

urlpatterns = router.urls
