"""
REST API for the human-in-the-loop admin workflow.

- Any system (the chatbot, a dashboard, curl) escalates a reservation via
  POST /reservations.
- The administrator approves/refuses via POST /reservations/{id}/decision.
- Anyone can poll GET /reservations/{id} or GET /reservations for status.

Mutating endpoints (POST) are protected by an optional API key
(ADMIN_API_KEY) sent as the `x-api-key` header -- if the env var isn't
set, auth is disabled (useful for local dev). Read endpoints are open.

Run with: uvicorn admin_agent.api:app --port 8001
Interactive docs: http://localhost:8001/docs
"""
import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from admin_agent.agent import AdminAgent
from admin_agent.models import RequestStatus

app = FastAPI(title="Parking Chatbot — Admin API")

_agent_instance: Optional[AdminAgent] = None


def get_agent() -> AdminAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AdminAgent()
    return _agent_instance


def verify_api_key(x_api_key: str = Header(default="")):
    expected = os.getenv("ADMIN_API_KEY", "")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


class EscalateRequest(BaseModel):
    first_name: str
    last_name: str
    car_number: str
    period_start: str
    period_end: str
    parking_lot: Optional[str] = None


class DecisionRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None


@app.post("/reservations", dependencies=[Depends(verify_api_key)])
def escalate(payload: EscalateRequest, agent: AdminAgent = Depends(get_agent)):
    request = agent.escalate(**payload.model_dump())
    return request.model_dump()


@app.get("/reservations/{request_id}")
def get_reservation(request_id: str, agent: AdminAgent = Depends(get_agent)):
    request = agent.get_decision(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request.model_dump()


@app.get("/reservations")
def list_reservations(status: Optional[RequestStatus] = None, agent: AdminAgent = Depends(get_agent)):
    return [r.model_dump() for r in agent.list_requests(status)]


@app.post("/reservations/{request_id}/decision", dependencies=[Depends(verify_api_key)])
def decide(request_id: str, payload: DecisionRequest, agent: AdminAgent = Depends(get_agent)):
    updated = agent.apply_decision(request_id, approved=payload.approved, reason=payload.reason)
    if not updated:
        raise HTTPException(status_code=404, detail="Request not found")
    return updated.model_dump()