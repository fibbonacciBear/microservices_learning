from datetime import datetime

from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1)


class CreateOrderRequest(BaseModel):
    items: list[OrderItemRequest] = Field(min_length=1)


class MenuItemResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    available: bool

    model_config = {"from_attributes": True}


class OrderItemDetailResponse(BaseModel):
    id: int
    menu_item_id: int
    name: str
    quantity: int
    unit_price: float
    line_total: float


class OrderSummaryResponse(BaseModel):
    id: int
    status: str
    total: float
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(BaseModel):
    id: int
    status: str
    total: float
    items: list[OrderItemDetailResponse]
    created_at: datetime
    updated_at: datetime | None


class KitchenQueueResponse(BaseModel):
    id: int
    order_id: int
    status: str
    started_at: datetime | None
    done_at: datetime | None

    model_config = {"from_attributes": True}


class KitchenCookResponse(BaseModel):
    order_id: int
    status: str


class NotificationResponse(BaseModel):
    id: int
    order_id: int
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
