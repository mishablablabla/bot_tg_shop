import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from db.session import Base

def gen_uuid():
    return str(uuid.uuid4())

class Relationship(Base):
    __tablename__ = "relationships"
    telegram_id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True)

    users = relationship("User", back_populates="referral")

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=gen_uuid)
    telegram_id = Column(Integer, unique=True, index=True)
    city = Column(String, nullable=True)
    referral_code = Column(String, ForeignKey("relationships.code"), nullable=True)

    referral = relationship("Relationship", back_populates="users")
    orders = relationship("Order", back_populates="user")

class Location(Base):
    __tablename__ = "locations"
    location_id = Column(String, primary_key=True, default=gen_uuid)
    region = Column(String)
    city = Column(String)

    stores = relationship("Store", back_populates="location")

class Store(Base):
    __tablename__ = "stores"
    store_id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String)
    location_id = Column(String, ForeignKey("locations.location_id"))

    location = relationship("Location", back_populates="stores")
    inventory = relationship("StoreProduct", back_populates="store")

class Product(Base):
    __tablename__ = "products"
    product_id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String)
    description = Column(Text)
    price = Column(Integer)

    inventory = relationship("StoreProduct", back_populates="product")
    orders = relationship("Order", back_populates="product")

class StoreProduct(Base):
    __tablename__ = "store_products"
    store_id = Column(String, ForeignKey("stores.store_id"), primary_key=True)
    product_id = Column(String, ForeignKey("products.product_id"), primary_key=True)
    quantity = Column(Integer)

    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"))
    product_id = Column(String, ForeignKey("products.product_id"))
    quantity = Column(Integer, default=1)
    status = Column(Enum("pending", "paid", "cancelled", name="order_status"), default="pending")

    user = relationship("User", back_populates="orders")
    product = relationship("Product", back_populates="orders")
