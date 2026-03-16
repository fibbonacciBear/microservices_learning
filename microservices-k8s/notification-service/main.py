from datetime import datetime

from fastapi import FastAPI

from schemas import CreateNotificationRequest, NotificationResponse


app = FastAPI(title="Notification Service")

notifications: list[NotificationResponse] = []
next_notification_id = 1


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/notifications", response_model=NotificationResponse, status_code=201)
def create_notification(payload: CreateNotificationRequest):
    global next_notification_id

    notification = NotificationResponse(
        id=next_notification_id,
        order_id=payload.order_id,
        message=payload.message,
        created_at=datetime.utcnow(),
    )
    next_notification_id += 1
    notifications.append(notification)
    return notification


@app.get("/notifications", response_model=list[NotificationResponse])
def list_notifications():
    return sorted(notifications, key=lambda item: (item.created_at, item.id), reverse=True)


@app.get("/notifications/{order_id}", response_model=list[NotificationResponse])
def list_order_notifications(order_id: int):
    order_notifications = [item for item in notifications if item.order_id == order_id]
    return sorted(order_notifications, key=lambda item: (item.created_at, item.id), reverse=True)
