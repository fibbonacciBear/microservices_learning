import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import KitchenQueue, Notification, Order
from schemas import KitchenCookResponse, KitchenQueueResponse


router = APIRouter()


@router.get("/queue", response_model=list[KitchenQueueResponse])
def list_queue(db: Session = Depends(get_db)):
    return db.query(KitchenQueue).order_by(KitchenQueue.id.asc()).all()


@router.post("/cook/{order_id}", response_model=KitchenCookResponse)
async def cook_order(order_id: int, db: Session = Depends(get_db)):
    queue_entry = db.query(KitchenQueue).filter(KitchenQueue.order_id == order_id).first()
    if queue_entry is None:
        raise HTTPException(status_code=404, detail="Kitchen queue entry not found")

    if queue_entry.status == "done":
        raise HTTPException(status_code=400, detail="Order already cooked")

    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    queue_entry.status = "cooking"
    queue_entry.started_at = datetime.utcnow()
    order.status = "preparing"
    db.add(Notification(order_id=order_id, message=f"Order #{order_id} is now preparing"))
    db.commit()

    time.sleep(5)

    queue_entry = db.query(KitchenQueue).filter(KitchenQueue.order_id == order_id).first()
    order = db.query(Order).filter(Order.id == order_id).first()
    queue_entry.status = "done"
    queue_entry.done_at = datetime.utcnow()
    order.status = "ready"
    db.add(Notification(order_id=order_id, message=f"Order #{order_id} is ready!"))
    db.commit()

    return KitchenCookResponse(order_id=order_id, status="cooking")
