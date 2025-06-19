from db.session import SessionLocal
from db.models import User, Relationship
import uuid

def is_valid_code(code: str) -> bool:
    db = SessionLocal()
    try:
        exists = db.query(Relationship).filter_by(code=code).first() is not None
    finally:
        db.close()
    return exists

def register_user(telegram_id: int, code: str) -> User:
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if existing_user:
            return existing_user

        rel = db.query(Relationship).filter_by(code=code).first()
        if not rel:
            raise ValueError(f"Referral code '{code}' is invalid")

        new_user = User(
            user_id=str(uuid.uuid4()),
            telegram_id=telegram_id,
            city=None,
            referral_code=rel.code
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)  
        return new_user
    finally:
        db.close()

def user_exists(telegram_id: int) -> bool:
    db = SessionLocal()
    try:
        return db.query(User).filter_by(telegram_id=telegram_id).first() is not None
    finally:
        db.close()

def get_user_by_telegram_id(telegram_id: int) -> User | None:
    db = SessionLocal()
    try:
        return db.query(User).filter_by(telegram_id=telegram_id).first()
    finally:
        db.close()
