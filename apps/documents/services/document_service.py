import hashlib
import logging
import os
from typing import Any, List

from django.db import transaction

from apps.authentication.models import User
from apps.collections.models import Collection
from apps.common.exceptions import AforroBaseException
from apps.documents.models import Document, DocumentVersion, Tag

logger = logging.getLogger(__name__)


class DocumentError(AforroBaseException):
    """Base exception for all document-related errors."""
    status_code = 400
    default_detail = "Document error occurred."
    default_code = "document_error"


class CollectionNotFoundError(DocumentError):
    """Raised when the target collection does not exist."""
    status_code = 404
    default_detail = "Target collection not found."
    default_code = "collection_not_found"


class DocumentNotFoundError(DocumentError):
    """Raised when the requested document does not exist."""
    status_code = 404
    default_detail = "Document not found."
    default_code = "document_not_found"


class DocumentService:
    """Service layer managing document ingestion, tags, version history, and storage tracking."""

    @classmethod
    @transaction.atomic
    def upload_document(
        cls,
        user: User,
        collection_id: int,
        file_obj: Any,
        title: str,
        description: str = "",
        tag_names: List[str] = None,
    ) -> Document:
        """
        Ingest a new document into a collection.
        
        Calculates file SHA-256 integrity hash, creates the Document metadata row,
        saves the initial DocumentVersion (v1), maps tags, and triggers async ingestion.
        """
        title = title.strip()
        if not title:
            raise DocumentError("Document title cannot be empty.")

        collection = cls._get_collection(collection_id)

        # 1. Calculate file metrics
        checksum = cls._calculate_checksum(file_obj)
        size_bytes = file_obj.size
        
        # Determine file extension/type
        filename = getattr(file_obj, "name", "")
        _, ext = os.path.splitext(filename)
        file_type = ext.lower().replace(".", "") or "txt"

        logger.info(
            "Ingesting document '%s' (%s, %d bytes) into collection %s by user %s.",
            title,
            file_type,
            size_bytes,
            collection.pk,
            user.username,
        )

        # 2. Create base Document metadata
        document = Document.objects.create(
            title=title,
            description=description,
            collection=collection,
            uploaded_by=user,
            file_type=file_type,
            status=Document.Status.PROCESSING,
        )

        # 3. Create DocumentVersion record (v1)
        DocumentVersion.objects.create(
            document=document,
            version_number=1,
            file=file_obj,
            size_bytes=size_bytes,
            checksum=checksum,
            uploaded_by=user,
        )

        # 4. Process and link tags
        if tag_names:
            cls._link_tags_to_document(document, tag_names)

        # 5. Dispatch async background parsing and vector indexing
        cls._dispatch_ingestion_task(document.pk)

        return document

    @classmethod
    @transaction.atomic
    def add_new_version(
        cls,
        user: User,
        document_id: int,
        file_obj: Any,
    ) -> DocumentVersion:
        """
        Upload a new version of an existing document.
        
        Increments the version number, calculates checksum, updates document status 
        to PROCESSING, and triggers the background ingestion task.
        """
        try:
            document = Document.objects.select_for_update().get(pk=document_id)
        except Document.DoesNotExist:
            raise DocumentNotFoundError()

        checksum = cls._calculate_checksum(file_obj)
        size_bytes = file_obj.size

        # Check if the file is identical to the latest version to prevent redundant processing
        latest_version = document.versions.order_by("-version_number").first()
        if latest_version and latest_version.checksum == checksum:
            logger.info("Uploaded file matches latest version checksum %s. Skipping upload.", checksum)
            return latest_version

        next_version_number = (latest_version.version_number + 1) if latest_version else 1

        logger.info(
            "Adding version v%d to document '%s' (ID: %d) by user %s.",
            next_version_number,
            document.title,
            document.pk,
            user.username,
        )

        # Create new version
        version = DocumentVersion.objects.create(
            document=document,
            version_number=next_version_number,
            file=file_obj,
            size_bytes=size_bytes,
            checksum=checksum,
            uploaded_by=user,
        )

        # Reset document status to processing
        document.status = Document.Status.PROCESSING
        document.save(update_fields=["status", "updated_at"])

        # Dispatch async background task
        cls._dispatch_ingestion_task(document.pk)

        return version

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _get_collection(collection_id: int) -> Collection:
        try:
            return Collection.objects.get(pk=collection_id)
        except Collection.DoesNotExist:
            raise CollectionNotFoundError()

    @staticmethod
    def _calculate_checksum(file_obj: Any) -> str:
        """Calculate the SHA-256 hash of an uploaded file."""
        hash_sha256 = hashlib.sha256()
        try:
            # Ensure file pointer is at start
            file_obj.seek(0)
            for chunk in iter(lambda: file_obj.read(4096), b""):
                hash_sha256.update(chunk)
            file_obj.seek(0)  # Reset pointer for Django's saver
            return hash_sha256.hexdigest()
        except Exception as exc:
            logger.error("Failed to calculate file checksum: %s", str(exc))
            raise DocumentError("Failed to verify file integrity.")

    @staticmethod
    def _link_tags_to_document(document: Document, tag_names: List[str]) -> None:
        """Link tags to document, creating tags dynamically if they do not exist."""
        tags = []
        for name in tag_names:
            name_clean = name.strip().lower()
            if name_clean:
                tag, _ = Tag.objects.get_or_create(name=name_clean)
                tags.append(tag)
        document.tags.set(tags)

    @staticmethod
    def _dispatch_ingestion_task(document_id: int) -> None:
        """Dispatch async Celery task to parse text, chunk, and embed the document."""
        try:
            # We will implement this task in Phase 4. Currently, we catch ImportErrors and log.
            from apps.ai.tasks import process_document_ingestion
            process_document_ingestion.apply_async(args=[document_id], countdown=1)
            logger.info("Dispatched ingestion task for document ID: %d.", document_id)
        except ImportError:
            # Task not implemented yet; log and set status to ACTIVE directly for development/testing
            logger.warning(
                "Celery ingestion task not found (Phase 4). Setting document %d status to ACTIVE directly.",
                document_id,
            )
            # Fetch outside atomic block or update directly
            Document.objects.filter(pk=document_id).update(status=Document.Status.ACTIVE)
        except Exception as exc:
            logger.error("Failed to dispatch ingestion task for document %d: %s", document_id, exc)
            # Avoid rolling back transaction; background failures shouldn't crash the upload API
            Document.objects.filter(pk=document_id).update(status=Document.Status.FAILED)
