from fastapi.testclient import TestClient

from admin_agent.api import app, get_agent
from admin_agent.models import ReservationRequest, RequestStatus


class _FakeAgent:
    def __init__(self):
        self._requests = {}

    def escalate(self, **kwargs):
        req = ReservationRequest(id="req-1", status=RequestStatus.PENDING, **kwargs)
        self._requests[req.id] = req
        return req

    def get_decision(self, request_id):
        return self._requests.get(request_id)

    def list_requests(self, status=None):
        values = list(self._requests.values())
        return [r for r in values if status is None or r.status == status]

    def apply_decision(self, request_id, approved, reason=None):
        req = self._requests.get(request_id)
        if not req:
            return None
        req.status = RequestStatus.APPROVED if approved else RequestStatus.REFUSED
        req.decision_reason = reason
        return req


def _client_with_fake_agent():
    fake_agent = _FakeAgent()
    app.dependency_overrides[get_agent] = lambda: fake_agent
    return TestClient(app), fake_agent


def test_escalate_endpoint_creates_request():
    client, _ = _client_with_fake_agent()
    response = client.post("/reservations", json={
        "first_name": "Jane", "last_name": "Doe", "car_number": "ABC123",
        "period_start": "9am", "period_end": "11am",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    app.dependency_overrides.clear()


def test_get_reservation_returns_404_for_unknown_id():
    client, _ = _client_with_fake_agent()
    response = client.get("/reservations/does-not-exist")
    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_decision_endpoint_approves_request():
    client, _ = _client_with_fake_agent()
    client.post("/reservations", json={
        "first_name": "Jane", "last_name": "Doe", "car_number": "ABC123",
        "period_start": "9am", "period_end": "11am",
    })
    response = client.post("/reservations/req-1/decision", json={"approved": True, "reason": "ok"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    app.dependency_overrides.clear()


def test_decision_endpoint_requires_valid_api_key(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret123")
    client, _ = _client_with_fake_agent()
    response = client.post(
        "/reservations/req-1/decision",
        json={"approved": True},
        headers={"x-api-key": "wrong"},
    )
    assert response.status_code == 401
    app.dependency_overrides.clear()