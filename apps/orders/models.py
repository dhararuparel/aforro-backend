"""
Order domain models.

Contains Order and OrderItem models.

Order lifecycle:
    PENDING   → initial state (rarely persisted)
    CONFIRMED → all items had sufficient inventory; stock deducted
    REJECTED  → one or more items lacked stock; no stock deducted
"""

from django.core.validators import MinValueValidator
from django.db import models


class Order(models.Model):
    """
    Represents a customer order placed against a specific store.

    Status logic is owned by the order service; models are kept dumb.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="orders",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]
        indexes = [
            # Supports GET /api/stores/{id}/orders/ sorted by newest
            models.Index(fields=["store", "-created_at"], name="idx_order_store_date"),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} [{self.status}] - {self.store.name}"


class OrderItem(models.Model):
    """
    A single line item within an order.

    quantity_requested reflects what was asked for at order time,
    regardless of whether the order was confirmed or rejected.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
        db_index=True,
    )
    quantity_requested = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self) -> str:
        return f"Order #{self.order_id} - {self.product.title} x{self.quantity_requested}"
