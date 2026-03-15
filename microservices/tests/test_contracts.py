import httpx


def test_menu_contract(base_url: str):
    response = httpx.get(f"{base_url}/menu", timeout=5)
    response.raise_for_status()

    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    first = payload[0]
    assert {"id", "name", "price", "available"} <= first.keys()


def test_orders_contract(base_url: str):
    response = httpx.post(
        f"{base_url}/orders",
        json={"items": [{"menu_item_id": 1, "quantity": 1}]},
        timeout=5,
    )
    response.raise_for_status()

    payload = response.json()
    assert {"id", "status", "total"} <= payload.keys()


def test_kitchen_queue_contract(base_url: str):
    response = httpx.get(f"{base_url}/kitchen/queue", timeout=5)
    response.raise_for_status()

    payload = response.json()
    assert isinstance(payload, list)
    if payload:
      assert {"order_id", "status"} <= payload[0].keys()


def test_notifications_contract(base_url: str):
    response = httpx.get(f"{base_url}/notifications", timeout=5)
    response.raise_for_status()

    payload = response.json()
    assert isinstance(payload, list)
    if payload:
      assert {"order_id", "message"} <= payload[0].keys()
