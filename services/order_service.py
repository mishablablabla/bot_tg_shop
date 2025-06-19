from db.session import SessionLocal
from db.models import Order, User, Product

def create_order(telegram_id, region, city, store, product_name):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    product = db.query(Product).filter_by(name=product_name).first()
    order = Order(user_id=user.user_id, product_id=product.product_id, quantity=1)
    db.add(order); db.commit()
    db.refresh(order); db.close()
    return order
