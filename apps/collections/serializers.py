from rest_framework import serializers

from apps.authentication.serializers import UserSerializer
from apps.collections.models import Collection


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection CRUD operations."""

    created_by_detail = UserSerializer(source="created_by", read_only=True)

    class Meta:
        model = Collection
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "created_by_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]
