from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Notification
from schemas import NotificationResponse


router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
def list_notifications(db: Session = Depends(get_db)):
    return (
        db.query(Notification)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )


@router.get("/{order_id}", response_model=list[NotificationResponse])
def list_order_notifications(order_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Notification)
        .filter(Notification.order_id == order_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
