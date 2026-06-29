from rest_framework import serializers

from apps.authentication.serializers import UserSerializer
from apps.collections.serializers import CollectionSerializer
from apps.documents.models import Document, DocumentVersion, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_detail = UserSerializer(source="uploaded_by", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "version_number",
            "size_bytes",
            "checksum",
            "uploaded_by",
            "uploaded_by_detail",
            "uploaded_at",
            "file_url",
        ]

    def get_file_url(self, obj: DocumentVersion) -> str:
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model."""

    uploaded_by_detail = UserSerializer(source="uploaded_by", read_only=True)
    collection_detail = CollectionSerializer(source="collection", read_only=True)
    tags_detail = TagSerializer(source="tags", many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()

    # Write-only fields for multipart file upload
    file = serializers.FileField(write_only=True, required=False)
    tag_list = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "description",
            "collection",
            "collection_detail",
            "uploaded_by",
            "uploaded_by_detail",
            "tags",
            "tags_detail",
            "file_type",
            "status",
            "created_at",
            "updated_at",
            "latest_version",
            "file",
            "tag_list",
        ]
        read_only_fields = [
            "id",
            "uploaded_by",
            "file_type",
            "status",
            "tags",
            "created_at",
            "updated_at",
        ]

    def get_latest_version(self, obj: Document) -> dict | None:
        latest = obj.versions.order_by("-version_number").first()
        if latest:
            return DocumentVersionSerializer(latest, context=self.context).data
        return None
