from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import KitchenQueue, MenuItem, Notification, Order, OrderItem
from schemas import CreateOrderRequest, OrderDetailResponse, OrderItemDetailResponse, OrderSummaryResponse


router = APIRouter()


def build_order_detail(order: Order) -> OrderDetailResponse:
    return OrderDetailResponse(
        id=order.id,
        status=order.status,
        total=order.total,
        items=[
            OrderItemDetailResponse(
                id=item.id,
                menu_item_id=item.menu_item_id,
                name=item.menu_item.name,
                quantity=item.quantity,
                unit_price=item.menu_item.price,
                line_total=item.menu_item.price * item.quantity,
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db)):
    menu_items = (
        db.query(MenuItem)
        .filter(MenuItem.id.in_([item.menu_item_id for item in payload.items]))
        .all()
    )
    menu_item_map = {item.id: item for item in menu_items}

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
        if not menu_item_map[item.menu_item_id].available
    ]
    if unavailable_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Menu items unavailable: {', '.join(map(str, sorted(set(unavailable_ids))))}",
        )

    total = sum(menu_item_map[item.menu_item_id].price * item.quantity for item in payload.items)

    order = Order(status="placed", total=round(total, 2))
    db.add(order)
    db.flush()

    order_items = [
        OrderItem(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
        )
        for item in payload.items
    ]
    db.add_all(order_items)
    db.add(KitchenQueue(order_id=order.id, status="queued"))
    db.add(Notification(order_id=order.id, message=f"Order #{order.id} placed"))
    db.commit()

    created_order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.menu_item))
        .filter(Order.id == order.id)
        .first()
    )
    return build_order_detail(created_order)


@router.get("", response_model=list[OrderSummaryResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).all()


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.menu_item))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return build_order_detail(order)
