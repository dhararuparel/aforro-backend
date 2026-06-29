from django.conf import settings
from django.db import models


class Collection(models.Model):
    """
    A workspace or folder grouping related documents.
    
    Replaces the 'Store' model from the legacy design.
    """

    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="collections",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Collection"
        verbose_name_plural = "Collections"

    def __str__(self) -> str:
        return self.name
