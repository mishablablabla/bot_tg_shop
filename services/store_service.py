from db.session import SessionLocal
from db.models import Location, Store

def list_regions():
    db = SessionLocal()
    try:
        regions = db.query(Location.region).distinct().all()
        return sorted([r[0] for r in regions]) 
    finally:
        db.close()

def list_cities(region: str):
    db = SessionLocal()
    try:
        cities = [c.city for c in db.query(Location).filter_by(region=region)]
        return sorted(cities)  
    finally:
        db.close()

def list_stores(region: str, city: str):
    db = SessionLocal()
    try:
        loc = db.query(Location).filter_by(region=region, city=city).first()
        if not loc:
            return []
        shops = [s.name for s in loc.stores]
        return sorted(shops) 
    finally:
        db.close()