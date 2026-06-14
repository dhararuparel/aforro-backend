"""
Celery tasks for the orders app.

Worker startup instructions:
    # Development (single worker, verbose logging)
    celery -A config worker --loglevel=info

    # Production (4 concurrent workers)
    celery -A config worker --loglevel=info --concurrency=4 --queues=default

    # Via Docker Compose (defined in docker-compose.yml)
    docker-compose up celery
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
    name="orders.send_order_confirmation",
)
def send_order_confirmation(self, order_id: int) -> dict:
    """
    Send an order confirmation notification after a successful order.

    This task is triggered automatically after any CONFIRMED order is created.
    It runs asynchronously so the API response is not blocked.

    In a real production system, this would:
      - Send a confirmation email to the customer
      - Send a push notification
      - Notify warehouse management systems
      - Update any downstream analytics pipelines

    Args:
        order_id: Primary key of the confirmed Order.

    Returns:
        Dict with task result metadata.

    Raises:
        self.retry(): On transient errors (e.g., SMTP timeout, network issue).
    """
    try:
        from apps.orders.models import Order

        order = Order.objects.select_related("store").prefetch_related("items__product").get(
            pk=order_id
        )

        # Simulate sending confirmation (replace with real notification logic)
        item_count = order.items.count()
        logger.info(
            "[ORDER CONFIRMATION] Order #%s for store '%s' confirmed at %s. "
            "%d item(s). Task executed at %s.",
            order.pk,
            order.store.name,
            order.created_at.isoformat(),
            item_count,
            timezone.now().isoformat(),
        )

        # In production, you would call your notification service here:
        # notification_service.send_order_confirmation(order)
        # email_service.send(to=order.customer.email, template="order_confirmed", context={...})

        return {
            "order_id": order_id,
            "store": order.store.name,
            "status": "confirmation_sent",
            "item_count": item_count,
        }

    except Exception as exc:
        logger.error(
            "Error processing confirmation for order #%s: %s",
            order_id,
            str(exc),
            exc_info=True,
        )
        # Retry on failure with exponential-like backoff
        raise self.retry(exc=exc)
