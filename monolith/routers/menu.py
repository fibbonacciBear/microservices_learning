from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import MenuItem
from schemas import MenuItemResponse


router = APIRouter()


@router.get("", response_model=list[MenuItemResponse])
def list_menu(db: Session = Depends(get_db)):
    return db.query(MenuItem).order_by(MenuItem.id.asc()).all()


@router.get("/{item_id}", response_model=MenuItemResponse)
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item
