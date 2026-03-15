import os
import time
from datetime import datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import KitchenQueue
from schemas import CreateKitchenOrderRequest, KitchenCookResponse, KitchenQueueResponse


ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:5002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:5004")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "3"))
NOTIFICATION_TIMEOUT_SECONDS = float(os.getenv("NOTIFICATION_TIMEOUT_SECONDS", "2"))

app = FastAPI(title="Kitchen Service")


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


async def update_order_status(order_id: int, new_status: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
            json={"status": new_status},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()


async def send_notification(order_id: int, message: str) -> None:
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications",
                json={"order_id": order_id, "message": message},
                timeout=NOTIFICATION_TIMEOUT_SECONDS,
            )
    except httpx.HTTPError:
        pass


@app.get("/kitchen/queue", response_model=list[KitchenQueueResponse])
def list_queue(db: Session = Depends(get_db)):
    return db.query(KitchenQueue).order_by(KitchenQueue.id.asc()).all()


@app.post(
    "/kitchen/orders",
    response_model=KitchenQueueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_kitchen_order(
    payload: CreateKitchenOrderRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    queue_entry = db.query(KitchenQueue).filter(KitchenQueue.order_id == payload.order_id).first()
    if queue_entry is not None:
        response.status_code = status.HTTP_200_OK
        return queue_entry

    queue_entry = KitchenQueue(order_id=payload.order_id, status="queued")
    db.add(queue_entry)
    db.commit()
    db.refresh(queue_entry)
    return queue_entry


@app.post("/kitchen/cook/{order_id}", response_model=KitchenCookResponse)
async def cook_order(order_id: int, db: Session = Depends(get_db)):
    queue_entry = db.query(KitchenQueue).filter(KitchenQueue.order_id == order_id).first()
    if queue_entry is None:
        raise HTTPException(status_code=404, detail="Kitchen queue entry not found")

    if queue_entry.status == "done":
        raise HTTPException(status_code=400, detail="Order already cooked")

    if queue_entry.status == "queued":
        try:
            await update_order_status(order_id, "preparing")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Order service unavailable") from exc

        queue_entry.status = "cooking"
        queue_entry.started_at = datetime.utcnow()
        db.commit()
        await send_notification(order_id, f"Order #{order_id} is now preparing")
        time.sleep(5)

    try:
        await update_order_status(order_id, "ready")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Order service unavailable") from exc

    queue_entry = db.query(KitchenQueue).filter(KitchenQueue.order_id == order_id).first()
    queue_entry.status = "done"
    queue_entry.done_at = datetime.utcnow()
    db.commit()
    await send_notification(order_id, f"Order #{order_id} is ready!")

    return KitchenCookResponse(order_id=order_id, status="cooking")
