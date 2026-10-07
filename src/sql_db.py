"""
Dynamic parking data (hours, prices, live availability) lives in SQL,
while static knowledge (general info, location, booking process, policies)
lives in the vector store, ingested from PDFs (see data/ingest.py).
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings

Base = declarative_base()


class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    location = Column(String)
    opening_hour = Column(String)
    closing_hour = Column(String)
    price_per_hour = Column(Float)
    total_slots = Column(Integer)
    available_slots = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow)


_engine_cache = {}


def _get_engine(db_path: str = None):
    path = db_path or settings.SQL_DB_PATH
    if path not in _engine_cache:
        engine = create_engine(f"sqlite:///{path}", echo=False)
        Base.metadata.create_all(engine)
        _engine_cache[path] = engine
    return _engine_cache[path]


def _session(db_path: str = None):
    return sessionmaker(bind=_get_engine(db_path))()


def init_db(db_path: str = None):
    _get_engine(db_path)


def seed_db(db_path: str = None):
    init_db(db_path)
    session = _session(db_path)
    try:
        if session.query(ParkingLot).count() == 0:
            session.add_all(
                [
                    ParkingLot(name="Downtown Garage", location="123 Main St",
                               opening_hour="06:00", closing_hour="23:00",
                               price_per_hour=3.5, total_slots=120, available_slots=42),
                    ParkingLot(name="Airport Parking", location="Airport Rd, Terminal 2",
                               opening_hour="00:00", closing_hour="23:59",
                               price_per_hour=5.0, total_slots=300, available_slots=87),
                    ParkingLot(name="Mall Parking", location="456 Market Ave",
                               opening_hour="08:00", closing_hour="22:00",
                               price_per_hour=2.0, total_slots=200, available_slots=0),
                ]
            )
            session.commit()
    finally:
        session.close()


def list_lots(db_path: str = None):
    session = _session(db_path)
    try:
        return session.query(ParkingLot).all()
    finally:
        session.close()


def get_lot_by_name(name: str, db_path: str = None):
    session = _session(db_path)
    try:
        return session.query(ParkingLot).filter(ParkingLot.name.ilike(f"%{name}%")).first()
    finally:
        session.close()


def update_availability(name: str, delta: int, db_path: str = None):
    session = _session(db_path)
    try:
        lot = session.query(ParkingLot).filter(ParkingLot.name.ilike(f"%{name}%")).first()
        if lot:
            lot.available_slots = max(0, lot.available_slots + delta)
            lot.updated_at = datetime.utcnow()
            session.commit()
    finally:
        session.close()