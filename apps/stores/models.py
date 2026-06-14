"""
Store domain models.

Contains Store and Inventory models.
Inventory is the join table between Store and Product,
extended with a quantity field.
"""

from django.core.validators import MinValueValidator
from django.db import models


class Store(models.Model):
    """
    Represents a physical or virtual store location.

    Indexed on name for search and display queries.
    """

    name = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=500)

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Inventory(models.Model):
    """
    Tracks how many units of a given product a store carries.

    Constraints:
        - unique(store, product): a store can only have one
          inventory record per product.
        - quantity >= 0: enforced at DB and application level.

    The cache key for a store's full inventory list is:
        inventory_store_{store_id}

    This is invalidated via Django signals (see signals.py) whenever
    an Inventory record is saved or deleted.
    """

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="inventory_items",
        db_index=True,
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory_items",
        db_index=True,
    )
    quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Inventory"
        verbose_name_plural = "Inventory"
        unique_together = [("store", "product")]
        indexes = [
            # Supports inventory listing sorted by product title
            models.Index(fields=["store", "product"], name="idx_inventory_store_product"),
        ]

    def __str__(self) -> str:
        return f"{self.store.name} - {self.product.title}: {self.quantity}"
