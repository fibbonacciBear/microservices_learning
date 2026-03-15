from sqlalchemy.orm import Session

from models import MenuItem


DEFAULT_MENU_ITEMS = [
    {
        "name": "Margherita",
        "description": "Classic tomato sauce and mozzarella",
        "price": 9.99,
    },
    {
        "name": "Pepperoni",
        "description": "Mozzarella and spicy pepperoni",
        "price": 11.99,
    },
    {
        "name": "Hawaiian",
        "description": "Ham and pineapple",
        "price": 12.49,
    },
    {
        "name": "Veggie Supreme",
        "description": "Bell peppers, olives, onions, mushrooms",
        "price": 13.99,
    },
    {
        "name": "BBQ Chicken",
        "description": "BBQ sauce, grilled chicken, red onion",
        "price": 14.49,
    },
]


def seed_menu(db: Session) -> None:
    if db.query(MenuItem).count() > 0:
        return

    db.add_all([MenuItem(**item, available=True) for item in DEFAULT_MENU_ITEMS])
    db.commit()
