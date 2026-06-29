import logging
from typing import Any

from django.db import transaction

from apps.authentication.models import User
from apps.collections.models import Collection
from apps.common.exceptions import AforroBaseException

logger = logging.getLogger(__name__)


class CollectionError(AforroBaseException):
    """Base exception for all collection-related errors."""
    status_code = 400
    default_detail = "Collection error occurred."
    default_code = "collection_error"


class CollectionAlreadyExistsError(CollectionError):
    """Raised when trying to create a collection with a name that already exists."""
    status_code = 400
    default_detail = "A collection with this name already exists."
    default_code = "collection_already_exists"


class CollectionService:
    """Service layer managing collection lifecycle, validation, and permissions."""

    @classmethod
    @transaction.atomic
    def create_collection(cls, user: User, name: str, description: str = "") -> Collection:
        """
        Create a new document collection (workspace).
        
        Validates unique name and assigns the creating user as owner.
        """
        name = name.strip()
        if not name:
            raise CollectionError("Collection name cannot be empty.")

        if Collection.objects.filter(name__iexact=name).exists():
            raise CollectionAlreadyExistsError()

        try:
            logger.info("User %s is creating collection '%s'.", user.username, name)
            collection = Collection.objects.create(
                name=name,
                description=description,
                created_by=user,
            )
            return collection
        except Exception as exc:
            logger.error("Failed to create collection '%s': %s", name, str(exc), exc_info=True)
            raise CollectionError("An unexpected error occurred while creating the collection.")
