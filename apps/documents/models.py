from django.conf import settings
from django.db import models


class Tag(models.Model):
    """
    Flat metadata tags for document categorization.
    
    Replaces the 'Category' model from the legacy design.
    """

    name = models.CharField(max_length=50, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:
        return self.name


class Document(models.Model):
    """
    Core document record. Tracks ingestion status, collection, and owner.
    
    Replaces the 'Product' model from the legacy design.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        ACTIVE = "ACTIVE", "Active"
        FAILED = "FAILED", "Failed"

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    collection = models.ForeignKey(
        "collections.Collection",
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
        db_index=True,
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="documents")
    file_type = models.CharField(max_length=20, db_index=True)  # e.g., "pdf", "txt", "docx"
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        indexes = [
            models.Index(fields=["collection", "status"], name="idx_doc_collection_status"),
            models.Index(fields=["collection", "-created_at"], name="idx_doc_collection_date"),
        ]

    def __str__(self) -> str:
        return self.title


class DocumentVersion(models.Model):
    """
    Tracks historical uploads and raw physical files.
    
    Replaces the 'Inventory' model from the legacy design.
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
        db_index=True,
    )
    version_number = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    size_bytes = models.BigIntegerField()
    checksum = models.CharField(max_length=64, db_index=True)  # SHA-256 hash to identify duplicate files
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_versions",
        db_index=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = (("document", "version_number"),)
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"

    def __str__(self) -> str:
        return f"{self.document.title} - v{self.version_number}"
