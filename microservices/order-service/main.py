import asyncio
import contextlib
import os
from collections.abc import AsyncIterator

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from database import Base, SessionLocal, engine, get_db
from models import Order, OrderItem
from schemas import (
    CreateOrderRequest,
    KitchenOrderRequest,
    OrderDetailResponse,
    OrderItemDetailResponse,
    OrderSummaryResponse,
    UpdateOrderStatusRequest,
)


MENU_SERVICE_URL = os.getenv("MENU_SERVICE_URL", "http://menu-service:5001")
KITCHEN_SERVICE_URL = os.getenv("KITCHEN_SERVICE_URL", "http://kitchen-service:5003")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:5004")
RECONCILE_INTERVAL_SECONDS = float(os.getenv("RECONCILE_INTERVAL_SECONDS", "30"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "3"))
NOTIFICATION_TIMEOUT_SECONDS = float(os.getenv("NOTIFICATION_TIMEOUT_SECONDS", "2"))
VALID_ORDER_STATUSES = {"placed", "pending", "preparing", "ready", "delivered"}

reconcile_task: asyncio.Task | None = None


def build_order_detail(order: Order) -> OrderDetailResponse:
    return OrderDetailResponse(
        id=order.id,
        status=order.status,
        total=order.total,
        items=[
            OrderItemDetailResponse(
                id=item.id,
                menu_item_id=item.menu_item_id,
                name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.unit_price * item.quantity,
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


async def fetch_menu_items(client: httpx.AsyncClient) -> dict[int, dict]:
    response = await client.get(
        f"{MENU_SERVICE_URL}/menu",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    items = response.json()
    return {item["id"]: item for item in items}


async def send_notification(order_id: int, message: str) -> None:
    payload = {"order_id": order_id, "message": message}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications",
                json=payload,
                timeout=NOTIFICATION_TIMEOUT_SECONDS,
            )
    except httpx.HTTPError:
        pass


async def enqueue_with_kitchen(order_id: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{KITCHEN_SERVICE_URL}/kitchen/orders",
                json=KitchenOrderRequest(order_id=order_id).model_dump(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


async def reconcile_pending_orders() -> None:
    while True:
        await asyncio.sleep(RECONCILE_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            pending_orders = (
                db.query(Order)
                .filter(Order.status == "pending")
                .order_by(Order.created_at.asc(), Order.id.asc())
                .all()
            )
            for order in pending_orders:
                if await enqueue_with_kitchen(order.id):
                    order.status = "placed"
                    db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global reconcile_task

    Base.metadata.create_all(bind=engine)
    reconcile_task = asyncio.create_task(reconcile_pending_orders())
    try:
        yield
    finally:
        if reconcile_task is not None:
            reconcile_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reconcile_task


app = FastAPI(title="Order Service", lifespan=lifespan)


@app.post("/orders", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        try:
            menu_item_map = await fetch_menu_items(client)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Menu service unavailable") from exc

    missing_item_ids = [
        item.menu_item_id for item in payload.items if item.menu_item_id not in menu_item_map
    ]
    if missing_item_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Menu items not found: {', '.join(map(str, sorted(set(missing_item_ids))))}",
        )

    unavailable_ids = [
        item.menu_item_id
        for item in payload.items
        if not menu_item_map[item.menu_item_id]["available"]
    ]
    if unavailable_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Menu items unavailable: {', '.join(map(str, sorted(set(unavailable_ids))))}",
        )

    total = sum(menu_item_map[item.menu_item_id]["price"] * item.quantity for item in payload.items)
    order = Order(status="placed", total=round(total, 2))
    db.add(order)
    db.flush()

    db.add_all(
        [
            OrderItem(
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                item_name=menu_item_map[item.menu_item_id]["name"],
                unit_price=menu_item_map[item.menu_item_id]["price"],
                quantity=item.quantity,
            )
            for item in payload.items
        ]
    )
    db.commit()

    if not await enqueue_with_kitchen(order.id):
        order = db.query(Order).filter(Order.id == order.id).first()
        order.status = "pending"
        db.commit()

    await send_notification(order.id, f"Order #{order.id} placed")

    created_order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order.id)
        .first()
    )
    return build_order_detail(created_order)


@app.get("/orders", response_model=list[OrderSummaryResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).all()


@app.get("/orders/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return build_order_detail(order)


@app.put("/orders/{order_id}/status", response_model=OrderDetailResponse)
def update_order_status(
    order_id: int,
    payload: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
):
    if payload.status not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status")

    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return build_order_detail(order)
