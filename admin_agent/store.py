"""
Shared, SQLite-backed store for reservation requests. This is the
communication channel between the two agents: the user-facing chatbot
(Agent 1) creates PENDING records here, the admin agent (Agent 2) updates
them with a decision, and the chatbot polls this same store to relay the
decision back to the user.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from admin_agent.models import ReservationRequest, RequestStatus
from src.config import settings

Base = declarative_base()


class ReservationRequestRecord(Base):
    __tablename__ = "reservation_requests"

    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    car_number = Column(String)
    period_start = Column(String)
    period_end = Column(String)
    parking_lot = Column(String, nullable=True)
    status = Column(String, default=RequestStatus.PENDING.value)
    decision_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)


_engine_cache = {}


def _get_engine(db_path: str = None):
    path = db_path or settings.ADMIN_DB_PATH
    if path not in _engine_cache:
        engine = create_engine(f"sqlite:///{path}", echo=False)
        Base.metadata.create_all(engine)
        _engine_cache[path] = engine
    return _engine_cache[path]


def _session(db_path: str = None):
    return sessionmaker(bind=_get_engine(db_path))()


def init_db(db_path: str = None):
    _get_engine(db_path)


def _to_model(record: ReservationRequestRecord) -> ReservationRequest:
    return ReservationRequest(
        id=record.id, first_name=record.first_name, last_name=record.last_name,
        car_number=record.car_number, period_start=record.period_start,
        period_end=record.period_end, parking_lot=record.parking_lot,
        status=RequestStatus(record.status), decision_reason=record.decision_reason,
        created_at=record.created_at, decided_at=record.decided_at,
    )


def create_request(first_name, last_name, car_number, period_start, period_end,
                    parking_lot=None, db_path: str = None) -> ReservationRequest:
    session = _session(db_path)
    try:
        record = ReservationRequestRecord(
            id=str(uuid.uuid4()), first_name=first_name, last_name=last_name,
            car_number=car_number, period_start=period_start, period_end=period_end,
            parking_lot=parking_lot, status=RequestStatus.PENDING.value,
        )
        session.add(record)
        session.commit()
        return _to_model(record)
    finally:
        session.close()


def get_request(request_id: str, db_path: str = None) -> Optional[ReservationRequest]:
    session = _session(db_path)
    try:
        record = session.query(ReservationRequestRecord).filter_by(id=request_id).first()
        return _to_model(record) if record else None
    finally:
        session.close()


def list_requests(status: RequestStatus = None, db_path: str = None):
    session = _session(db_path)
    try:
        query = session.query(ReservationRequestRecord)
        if status:
            query = query.filter_by(status=status.value)
        return [_to_model(r) for r in query.all()]
    finally:
        session.close()


def set_decision(request_id: str, approved: bool, reason: str = None,
                  db_path: str = None) -> Optional[ReservationRequest]:
    session = _session(db_path)
    try:
        record = session.query(ReservationRequestRecord).filter_by(id=request_id).first()
        if not record:
            return None
        record.status = RequestStatus.APPROVED.value if approved else RequestStatus.REFUSED.value
        record.decision_reason = reason
        record.decided_at = datetime.utcnow()
        session.commit()
        return _to_model(record)
    finally:
        session.close()