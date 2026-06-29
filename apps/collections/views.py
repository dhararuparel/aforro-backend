import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.collections.models import Collection
from apps.collections.serializers import CollectionSerializer
from apps.collections.services.collection_service import CollectionService
from apps.common.permissions import IsOwnerOrAdmin

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=["Collections"], summary="List all collections"),
    retrieve=extend_schema(tags=["Collections"], summary="Get collection detail"),
    create=extend_schema(tags=["Collections"], summary="Create a collection"),
    update=extend_schema(tags=["Collections"], summary="Update a collection"),
    partial_update=extend_schema(tags=["Collections"], summary="Partially update a collection"),
    destroy=extend_schema(tags=["Collections"], summary="Delete a collection"),
)
class CollectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet managing Collection workspaces.
    
    Permissions:
        - List/Retrieve: Authenticated users
        - Create: Authenticated users
        - Update/Delete: Owner or Admin only
    """

    queryset = Collection.objects.select_related("created_by").all().order_by("-created_at")
    serializer_class = CollectionSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "validation_error",
                        "message": "Invalid collection data.",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = serializer.validated_data.get("name")
        description = serializer.validated_data.get("description", "")

        collection = CollectionService.create_collection(
            user=request.user,
            name=name,
            description=description,
        )

        response_serializer = self.get_serializer(collection)
        return Response(
            {
                "success": True,
                "message": "Collection created successfully.",
                "collection": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
