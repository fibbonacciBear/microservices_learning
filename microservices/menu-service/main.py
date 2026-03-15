from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from models import MenuItem
from schemas import MenuItemResponse
from seed import seed_menu


app = FastAPI(title="Menu Service")


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_menu(db)
    finally:
        db.close()


@app.get("/menu", response_model=list[MenuItemResponse])
def list_menu(db: Session = Depends(get_db)):
    return db.query(MenuItem).order_by(MenuItem.id.asc()).all()


@app.get("/menu/{item_id}", response_model=MenuItemResponse)
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item
