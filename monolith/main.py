from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from routers.kitchen import router as kitchen_router
from routers.menu import router as menu_router
from routers.notifications import router as notifications_router
from routers.orders import router as orders_router
from seed import seed_menu


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Pizza Shop Monolith")


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_menu(db)
    finally:
        db.close()


app.include_router(menu_router, prefix="/menu", tags=["Menu"])
app.include_router(orders_router, prefix="/orders", tags=["Orders"])
app.include_router(kitchen_router, prefix="/kitchen", tags=["Kitchen"])
app.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])

app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
