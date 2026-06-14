"""
Django signals for the stores app.

Handles cache invalidation for inventory changes.
When any Inventory record for a store is saved or deleted,
the cached inventory list for that store is automatically cleared.

Cache key format: inventory_store_{store_id}
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Inventory

logger = logging.getLogger(__name__)


def _invalidate_store_inventory_cache(store_id: int) -> None:
    """
    Delete the inventory cache for a given store.

    Called after any inventory save or delete to ensure
    the cached listing is never stale.
    """
    cache_key = f"inventory_store_{store_id}"
    deleted = cache.delete(cache_key)
    if deleted:
        logger.debug("Cache invalidated for store %s (key: %s)", store_id, cache_key)
    else:
        logger.debug(
            "Cache key %s was already absent (no invalidation needed).", cache_key
        )


@receiver(post_save, sender=Inventory)
def invalidate_inventory_cache_on_save(
    sender: type, instance: Inventory, **kwargs
) -> None:
    """Invalidate store inventory cache whenever an inventory row changes."""
    _invalidate_store_inventory_cache(instance.store_id)


@receiver(post_delete, sender=Inventory)
def invalidate_inventory_cache_on_delete(
    sender: type, instance: Inventory, **kwargs
) -> None:
    """Invalidate store inventory cache whenever an inventory row is deleted."""
    _invalidate_store_inventory_cache(instance.store_id)
