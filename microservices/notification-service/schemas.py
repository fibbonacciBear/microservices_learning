from datetime import datetime

from pydantic import BaseModel


class CreateNotificationRequest(BaseModel):
    order_id: int
    message: str


class NotificationResponse(BaseModel):
    id: int
    order_id: int
    message: str
    created_at: datetime
