import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import IsOwnerOrAdmin
from apps.documents.models import Document, DocumentVersion
from apps.documents.serializers import DocumentSerializer, DocumentVersionSerializer
from apps.documents.services.document_service import DocumentService

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=["Documents"], summary="List all documents"),
    retrieve=extend_schema(tags=["Documents"], summary="Get document detail"),
    update=extend_schema(tags=["Documents"], summary="Update document metadata"),
    partial_update=extend_schema(tags=["Documents"], summary="Partially update document metadata"),
    destroy=extend_schema(tags=["Documents"], summary="Delete a document"),
    upload_version=extend_schema(
        tags=["Documents"],
        summary="Upload a new version of a document",
        request=None,  # Handled by multipart
    ),
    versions=extend_schema(tags=["Documents"], summary="List document versions"),
)
class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet managing Document metadata, files, and version history.
    
    Query optimization:
        - select_related: collection, uploaded_by
        - prefetch_related: tags, versions
        
    Permissions:
        - List/Retrieve: Authenticated users
        - Create: Authenticated users
        - Update/Delete: Owner or Admin only
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return (
            Document.objects.select_related("collection", "uploaded_by")
            .prefetch_related("tags", "versions", "versions__uploaded_by")
            .all()
            .order_by("-created_at")
        )

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy", "upload_version"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Ingest a new document with its initial file version.
        
        Accepts: multipart/form-data
        Fields:
            - collection (int): Collection ID
            - title (str): Document title
            - description (str): Optional description
            - file (File): Physical file to upload
            - tag_list (list[str]): Optional list of tag names
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "validation_error",
                        "message": "Invalid document data.",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "missing_file",
                        "message": "A file upload is required for the initial document version.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        collection_id = serializer.validated_data.get("collection").pk
        title = serializer.validated_data.get("title")
        description = serializer.validated_data.get("description", "")
        tag_list = serializer.validated_data.get("tag_list", [])

        document = DocumentService.upload_document(
            user=request.user,
            collection_id=collection_id,
            file_obj=file_obj,
            title=title,
            description=description,
            tag_names=tag_list,
        )

        response_serializer = self.get_serializer(document)
        return Response(
            {
                "success": True,
                "message": "Document uploaded successfully and queued for ingestion.",
                "document": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="upload-version")
    def upload_version(self, request: Request, pk: str | None = None) -> Response:
        """
        Upload a new version of the existing document.
        
        Accepts: multipart/form-data containing a 'file' field.
        """
        document = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "missing_file",
                        "message": "A file is required to upload a new version.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        version = DocumentService.add_new_version(
            user=request.user,
            document_id=document.pk,
            file_obj=file_obj,
        )

        serializer = DocumentVersionSerializer(version, context={"request": request})
        return Response(
            {
                "success": True,
                "message": f"Successfully uploaded new version v{version.version_number}.",
                "version": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request: Request, pk: str | None = None) -> Response:
        """List all version history records for the document."""
        document = self.get_object()
        qs = document.versions.select_related("uploaded_by").all().order_by("-version_number")
        
        # Paginate results
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = DocumentVersionSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = DocumentVersionSerializer(qs, many=True, context={"request": request})
        return Response({"success": True, "results": serializer.data})
