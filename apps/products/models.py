"""
Product domain models.

Contains Category and Product models with proper indexing
for query performance.
"""

from django.db import models


class Category(models.Model):
    """
    Product category for grouping and filtering products.

    Indexed on name for fast lookups and search filtering.
    """

    name = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """
    Core product entity in the catalog.

    Indexes:
        - title: supports search/autocomplete
        - category: supports category filtering
        - price: supports range queries and sorting
        - created_at: supports sorting by newest
    """

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,  # Prevent accidental category deletion
        related_name="products",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            # Composite index for category + price range queries
            models.Index(fields=["category", "price"], name="idx_product_category_price"),
            # Composite index for category + newest sorting
            models.Index(fields=["category", "-created_at"], name="idx_product_category_date"),
        ]

    def __str__(self) -> str:
        return self.title
