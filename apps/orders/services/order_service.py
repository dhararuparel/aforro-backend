from dataclasses import dataclass, field
import logging
from typing import Any

from django.db import transaction

from apps.common.exceptions import InvalidOrderDataError, StoreNotFoundError
from apps.orders.models import Order, OrderItem
from apps.stores.models import Inventory, Store

logger = logging.getLogger(__name__)


@dataclass
class OrderItemInput:
    product_id: int
    quantity: int


@dataclass
class OrderResult:
    order: Order
    message: str
    stock_issues: list[dict[str, Any]] = field(default_factory=list)


class OrderService:
    """Service layer handling order validation, stock checks, and creation."""

    @classmethod
    def create_order(cls, store_id: int, items: list[dict[str, Any]]) -> OrderResult:
        """Create a new store order and dispatch confirmation task."""
        if not items:
            raise InvalidOrderDataError("Order must contain at least one item.")

        store = cls._get_store(store_id)
        item_inputs = [
            OrderItemInput(
                product_id=item["product_id"].pk,
                quantity=item["quantity"],
            )
            for item in items
        ]

        logger.info("Processing order for store %s with %d items.", store_id, len(item_inputs))
        result = cls._process_order_in_transaction(store, item_inputs)

        if result.order.status == Order.Status.CONFIRMED:
            cls._dispatch_confirmation_task(result.order.pk)

        return result

    @classmethod
    def _get_store(cls, store_id: int) -> Store:
        try:
            return Store.objects.get(pk=store_id)
        except Store.DoesNotExist:
            raise StoreNotFoundError()

    @classmethod
    @transaction.atomic
    def _process_order_in_transaction(cls, store: Store, item_inputs: list[OrderItemInput]) -> OrderResult:
        """Stock check and order updates inside a single database transaction."""
        product_ids = [item.product_id for item in item_inputs]

        # Lock inventory rows. Ordering by ID prevents deadlocks under concurrent requests.
        inventory_map: dict[int, Inventory] = {
            inv.product_id: inv
            for inv in Inventory.objects.select_for_update()
            .filter(store=store, product_id__in=product_ids)
            .select_related("product")
            .order_by("id")
        }

        stock_issues: list[dict[str, Any]] = []
        for item_input in item_inputs:
            inventory = inventory_map.get(item_input.product_id)

            if inventory is None:
                stock_issues.append({
                    "product_id": item_input.product_id,
                    "reason": "Product not found in store inventory.",
                    "available": 0,
                    "requested": item_input.quantity,
                })
            elif inventory.quantity < item_input.quantity:
                stock_issues.append({
                    "product_id": item_input.product_id,
                    "product_title": inventory.product.title,
                    "reason": "Insufficient stock.",
                    "available": inventory.quantity,
                    "requested": item_input.quantity,
                })

        if stock_issues:
            logger.warning("Order REJECTED for store %s - stock issues: %s", store.pk, stock_issues)
            order = Order.objects.create(store=store, status=Order.Status.REJECTED)
            cls._create_order_items(order, item_inputs, inventory_map)
            return OrderResult(
                order=order,
                message="Order rejected due to insufficient stock.",
                stock_issues=stock_issues,
            )

        order = Order.objects.create(store=store, status=Order.Status.CONFIRMED)
        cls._deduct_inventory(item_inputs, inventory_map)
        cls._create_order_items(order, item_inputs, inventory_map)

        logger.info("Order #%s CONFIRMED for store %s.", order.pk, store.pk)
        return OrderResult(order=order, message="Order confirmed successfully.")

    @staticmethod
    def _deduct_inventory(item_inputs: list[OrderItemInput], inventory_map: dict[int, Inventory]) -> None:
        """Deduct quantities from inventory rows in bulk."""
        to_update: list[Inventory] = []
        for item_input in item_inputs:
            inventory = inventory_map[item_input.product_id]
            inventory.quantity -= item_input.quantity
            to_update.append(inventory)

        Inventory.objects.bulk_update(to_update, ["quantity"])

    @staticmethod
    def _create_order_items(
        order: Order,
        item_inputs: list[OrderItemInput],
        inventory_map: dict[int, Inventory],
    ) -> None:
        """Bulk create all OrderItem records for audit tracking."""
        order_items = [
            OrderItem(
                order=order,
                product_id=item_input.product_id,
                quantity_requested=item_input.quantity,
            )
            for item_input in item_inputs
        ]
        OrderItem.objects.bulk_create(order_items)

    @staticmethod
    def _dispatch_confirmation_task(order_id: int) -> None:
        """Dispatch asynchronous Celery order confirmation task."""
        try:
            from apps.orders.tasks import send_order_confirmation
            send_order_confirmation.apply_async(args=[order_id], countdown=0)
            logger.info("Dispatched confirmation task for order #%s.", order_id)
        except Exception as exc:
            # Avoid rolling back transaction if Celery broker fails
            logger.error("Failed to dispatch confirmation task for order #%s: %s", order_id, exc, exc_info=True)
