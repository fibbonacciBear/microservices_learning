from datetime import datetime

from pydantic import BaseModel


class CreateKitchenOrderRequest(BaseModel):
    order_id: int


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
