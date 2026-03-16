from pydantic import BaseModel


class MenuItemResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    available: bool

    model_config = {"from_attributes": True}
