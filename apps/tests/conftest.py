"""
Pytest configuration and shared fixtures.

Fixtures are designed to be composable — complex fixtures build on simpler ones.
All DB fixtures use Django's pytest-django integration (db mark propagates automatically).
"""

import pytest
from decimal import Decimal

from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store
from apps.orders.models import Order, OrderItem


# ---------------------------------------------------------------------------
# Category fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def category(db) -> Category:
    """A single product category."""
    return Category.objects.create(name="Electronics")


@pytest.fixture
def category_clothing(db) -> Category:
    """A second product category for multi-category tests."""
    return Category.objects.create(name="Clothing")


# ---------------------------------------------------------------------------
# Product fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def product(db, category: Category) -> Product:
    """A standard product in the Electronics category."""
    return Product.objects.create(
        title="Test Laptop",
        description="A powerful laptop for testing.",
        price=Decimal("999.99"),
        category=category,
    )


@pytest.fixture
def product_cheap(db, category: Category) -> Product:
    """A low-price product for range filter tests."""
    return Product.objects.create(
        title="Budget Mouse",
        description="An affordable input device.",
        price=Decimal("9.99"),
        category=category,
    )


@pytest.fixture
def product_clothing(db, category_clothing: Category) -> Product:
    """A product in the Clothing category."""
    return Product.objects.create(
        title="Blue Jeans",
        description="Comfortable denim jeans.",
        price=Decimal("49.99"),
        category=category_clothing,
    )


# ---------------------------------------------------------------------------
# Store fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(db) -> Store:
    """A standard test store."""
    return Store.objects.create(name="Test Store", location="Lagos, NG")


@pytest.fixture
def store_b(db) -> Store:
    """A second test store."""
    return Store.objects.create(name="Store B", location="Abuja, NG")


# ---------------------------------------------------------------------------
# Inventory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def inventory(db, store: Store, product: Product) -> Inventory:
    """Inventory with sufficient stock (100 units)."""
    return Inventory.objects.create(store=store, product=product, quantity=100)


@pytest.fixture
def inventory_zero(db, store: Store, product_cheap: Product) -> Inventory:
    """Inventory with zero stock — used for rejection tests."""
    return Inventory.objects.create(store=store, product=product_cheap, quantity=0)


@pytest.fixture
def inventory_clothing(db, store: Store, product_clothing: Product) -> Inventory:
    """Inventory for clothing product."""
    return Inventory.objects.create(store=store, product=product_clothing, quantity=50)


# ---------------------------------------------------------------------------
# API client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    """DRF test client."""
    from rest_framework.test import APIClient
    return APIClient()
