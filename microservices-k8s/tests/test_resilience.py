import time

import httpx

from conftest import run_service_action, wait_for_url


def test_kitchen_unavailable_reconciles(base_url: str, orchestrator: str):
    run_service_action(orchestrator, "stop", "kitchen-service")
    try:
        response = httpx.post(
            f"{base_url}/orders",
            json={"items": [{"menu_item_id": 1, "quantity": 1}]},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        assert payload["status"] == "pending"
        order_id = payload["id"]
    finally:
        run_service_action(orchestrator, "start", "kitchen-service")

    wait_for_url(f"{base_url}/kitchen/queue")

    deadline = time.time() + 90
    while time.time() < deadline:
        order_response = httpx.get(f"{base_url}/orders/{order_id}", timeout=5)
        order_response.raise_for_status()
        order_payload = order_response.json()
        if order_payload["status"] == "placed":
            queue_response = httpx.get(f"{base_url}/kitchen/queue", timeout=5)
            queue_response.raise_for_status()
            assert any(item["order_id"] == order_id for item in queue_response.json())
            return
        time.sleep(2)

    raise AssertionError("Pending order did not reconcile before timeout")


def test_notification_outage_does_not_block_flow(base_url: str, orchestrator: str):
    run_service_action(orchestrator, "stop", "notification-service")
    try:
        order_response = httpx.post(
            f"{base_url}/orders",
            json={"items": [{"menu_item_id": 2, "quantity": 1}]},
            timeout=10,
        )
        order_response.raise_for_status()
        order_payload = order_response.json()
        order_id = order_payload["id"]

        cook_response = httpx.post(f"{base_url}/kitchen/cook/{order_id}", timeout=15)
        cook_response.raise_for_status()

        final_order_response = httpx.get(f"{base_url}/orders/{order_id}", timeout=5)
        final_order_response.raise_for_status()
        assert final_order_response.json()["status"] == "ready"
    finally:
        run_service_action(orchestrator, "start", "notification-service")
