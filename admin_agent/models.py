"""
Shared data model for the human-in-the-loop reservation approval workflow.
This is the contract both agents (user-facing chatbot and admin agent)
agree on when reading/writing through the shared RequestStore.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REFUSED = "refused"


class ReservationRequest(BaseModel):
    id: str
    first_name: str
    last_name: str
    car_number: str
    period_start: str
    period_end: str
    parking_lot: Optional[str] = None
    status: RequestStatus = RequestStatus.PENDING
    decision_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None