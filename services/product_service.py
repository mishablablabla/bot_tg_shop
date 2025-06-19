from db.session import SessionLocal
from db.models import Store, StoreProduct, Product

def list_products(region, city, store_name):
    db = SessionLocal()
    try:
        store = (
            db.query(Store)
            .join(Store.location)
            .filter(Store.name == store_name)
            .filter_by(region=region, city=city)
            .first()
        )
        if not store:
            return []

        items = []
        for inv in store.inventory:
            p = db.query(Product).get(inv.product_id)
            if p:
                items.append({"name": p.name, "price": p.price})
        return items
    finally:
        db.close()
