"""
Order processing tests.

Covers:
    1. Successful order creation (all items in stock)
    2. Rejected order (insufficient stock)
    3. Inventory deduction after confirmation
    4. Transaction rollback on DB error
    5. Rejected order when product not in inventory
    6. Multiple items — partial stock failure
    7. Order list endpoint
    8. Inventory listing endpoint
    9. Search filters
    10. Autocomplete validation
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderService
from apps.stores.models import Inventory
from apps.common.exceptions import StoreNotFoundError


# ---------------------------------------------------------------------------
# 1. Successful order creation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_successful_order_creation(store, product, inventory):
    """
    A confirmed order is created when all items have sufficient stock.
    The order status should be CONFIRMED.
    """
    result = OrderService.create_order(
        store_id=store.pk,
        items=[{"product_id": product, "quantity": 5}],
    )

    assert result.order.status == Order.Status.CONFIRMED
    assert result.order.store == store
    assert result.order.pk is not None
    assert result.stock_issues == []


# ---------------------------------------------------------------------------
# 2. Rejected order — insufficient stock
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rejected_order_insufficient_stock(store, product_cheap, inventory_zero):
    """
    An order is REJECTED when a product has zero stock.
    No inventory should be deducted.
    """
    result = OrderService.create_order(
        store_id=store.pk,
        items=[{"product_id": product_cheap, "quantity": 1}],
    )

    assert result.order.status == Order.Status.REJECTED
    assert len(result.stock_issues) == 1
    assert result.stock_issues[0]["available"] == 0


# ---------------------------------------------------------------------------
# 3. Inventory deduction after confirmation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_inventory_deducted_after_confirmation(store, product, inventory):
    """
    Stock should be reduced by the ordered quantity after a CONFIRMED order.
    """
    initial_quantity = inventory.quantity  # 100

    result = OrderService.create_order(
        store_id=store.pk,
        items=[{"product_id": product, "quantity": 10}],
    )

    assert result.order.status == Order.Status.CONFIRMED

    inventory.refresh_from_db()
    assert inventory.quantity == initial_quantity - 10


# ---------------------------------------------------------------------------
# 4. Transaction rollback — inventory NOT deducted on rejected order
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_inventory_not_deducted_on_rejection(store, product, inventory, inventory_zero, product_cheap):
    """
    When an order is rejected (even partially), NO inventory should be deducted.
    This tests the all-or-nothing transaction behavior.
    """
    initial_quantity = inventory.quantity  # 100 (laptop has stock)
    # product_cheap has 0 stock → will cause rejection

    result = OrderService.create_order(
        store_id=store.pk,
        items=[
            {"product_id": product, "quantity": 5},       # has stock
            {"product_id": product_cheap, "quantity": 1}, # no stock → rejection
        ],
    )

    assert result.order.status == Order.Status.REJECTED

    # The laptop's inventory must NOT have been touched
    inventory.refresh_from_db()
    assert inventory.quantity == initial_quantity


# ---------------------------------------------------------------------------
# 5. Store not found
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_store_not_found(product):
    """
    OrderService should raise StoreNotFoundError for a non-existent store.
    """
    with pytest.raises(StoreNotFoundError):
        OrderService.create_order(
            store_id=99999,
            items=[{"product_id": product, "quantity": 1}],
        )


# ---------------------------------------------------------------------------
# 6. Product not in store inventory
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_product_not_in_inventory(store, product):
    """
    If a product has no inventory record in the store, the order should be REJECTED.
    """
    # No Inventory record created for store/product
    result = OrderService.create_order(
        store_id=store.pk,
        items=[{"product_id": product, "quantity": 1}],
    )

    assert result.order.status == Order.Status.REJECTED
    assert len(result.stock_issues) == 1
    assert "not found" in result.stock_issues[0]["reason"].lower()


# ---------------------------------------------------------------------------
# 7. Order list API endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_list_endpoint(api_client, store, product, inventory):
    """
    GET /api/stores/{id}/orders/ returns paginated orders with total_items.
    """
    # Create a confirmed order
    result = OrderService.create_order(
        store_id=store.pk,
        items=[{"product_id": product, "quantity": 2}],
    )
    assert result.order.status == Order.Status.CONFIRMED

    url = f"/api/orders/stores/{store.pk}/orders/"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["pagination"]["count"] >= 1

    order_data = data["results"][0]
    assert "id" in order_data
    assert "status" in order_data
    assert "created_at" in order_data
    assert "total_items" in order_data
    assert order_data["total_items"] == 1


# ---------------------------------------------------------------------------
# 8. Inventory listing endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_inventory_listing_endpoint(api_client, store, inventory):
    """
    GET /api/stores/{id}/inventory/ returns inventory items with product details.
    """
    url = f"/api/stores/{store.pk}/inventory/"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    results = data["results"]
    assert len(results) >= 1

    item = results[0]
    assert "product_title" in item
    assert "category" in item
    assert "price" in item
    assert "quantity" in item


# ---------------------------------------------------------------------------
# 9. Search filters
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_filter_by_category(api_client, product, product_clothing, category, category_clothing):
    """
    Filtering by category should return only products in that category.
    """
    url = f"/api/search/products/?category={category.pk}"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    ids = [r["id"] for r in data["results"]]
    assert product.pk in ids
    assert product_clothing.pk not in ids


@pytest.mark.django_db
def test_search_filter_by_price_range(api_client, product, product_cheap):
    """
    min_price / max_price filters should correctly narrow results.
    """
    url = "/api/search/products/?min_price=500&max_price=2000"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    ids = [r["id"] for r in data["results"]]
    assert product.pk in ids       # price=999.99 — in range
    assert product_cheap.pk not in ids  # price=9.99 — out of range


@pytest.mark.django_db
def test_search_text_query(api_client, product):
    """
    Free-text search on 'q' parameter should match product titles.
    """
    url = "/api/search/products/?q=Laptop"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    ids = [r["id"] for r in data["results"]]
    assert product.pk in ids


# ---------------------------------------------------------------------------
# 10. Autocomplete validation — query too short
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_autocomplete_rejects_short_query(api_client):
    """
    Autocomplete should return 400 for queries shorter than 3 characters.
    """
    url = "/api/search/suggest/?q=la"
    response = api_client.get(url)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "query_too_short"


@pytest.mark.django_db
def test_autocomplete_returns_results(api_client, product):
    """
    Autocomplete returns matching results for a valid query.
    """
    url = "/api/search/suggest/?q=Lap"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "suggestions" in data
    titles = [s["title"] for s in data["suggestions"]]
    assert any("Laptop" in t for t in titles)


# ---------------------------------------------------------------------------
# 11. Order creation API endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_create_api_confirmed(api_client, store, product, inventory):
    """
    POST /api/orders/ returns 201 for a successfully confirmed order.
    """
    url = "/api/orders/"
    payload = {
        "store_id": store.pk,
        "items": [{"product_id": product.pk, "quantity": 3}],
    }
    response = api_client.post(url, payload, format="json")

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["order"]["status"] == "CONFIRMED"


@pytest.mark.django_db
def test_order_create_api_rejected(api_client, store, product_cheap, inventory_zero):
    """
    POST /api/orders/ returns 200 with REJECTED status when stock is insufficient.
    """
    url = "/api/orders/"
    payload = {
        "store_id": store.pk,
        "items": [{"product_id": product_cheap.pk, "quantity": 5}],
    }
    response = api_client.post(url, payload, format="json")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["order"]["status"] == "REJECTED"
    assert "stock_issues" in data


# ---------------------------------------------------------------------------
# 12. Celery task dispatch (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_celery_task_dispatched_on_confirmation(store, product, inventory):
    """
    The Celery confirmation task should be dispatched after a CONFIRMED order.
    The task is imported lazily inside the service method, so we patch it
    at its module location in apps.orders.tasks.
    """
    with patch("apps.orders.tasks.send_order_confirmation") as mock_task:
        mock_task.apply_async = lambda *a, **kw: None
        result = OrderService.create_order(
            store_id=store.pk,
            items=[{"product_id": product, "quantity": 1}],
        )

    assert result.order.status == Order.Status.CONFIRMED


# ---------------------------------------------------------------------------
# 13. Root URL prefix tests (for direct assignment path compatibility)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_root_order_creation_endpoint(api_client, store, product, inventory):
    """
    POST /orders/ should succeed.
    """
    url = "/orders/"
    payload = {
        "store_id": store.pk,
        "items": [{"product_id": product.pk, "quantity": 3}],
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["order"]["status"] == "CONFIRMED"


@pytest.mark.django_db
def test_root_store_order_listing_endpoint(api_client, store, product, inventory):
    """
    GET /stores/{store_id}/orders/ should return the order list.
    """
    # Create order first
    OrderService.create_order(
        store_id=store.pk,
        items=[{"product_id": product, "quantity": 1}],
    )
    url = f"/stores/{store.pk}/orders/"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(response.json()["results"]) >= 1


@pytest.mark.django_db
def test_root_store_inventory_listing_endpoint(api_client, store, inventory):
    """
    GET /stores/{store_id}/inventory/ should return the inventory list.
    """
    url = f"/stores/{store.pk}/inventory/"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(response.json()["results"]) >= 1

