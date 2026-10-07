from admin_agent.models import ReservationRequest, RequestStatus
from src.chatbot import ParkingChatbot
from src.reservation import ReservationDetails


class _FakeRag:
    def __init__(self, intent="static_info", answer="Static answer."):
        self.intent = intent
        self.answer = answer

    def classify_intent(self, _message):
        return self.intent

    def answer_static(self, _q):
        return {"answer": self.answer, "sources": ["doc1"]}

    def answer_dynamic(self, _q):
        return {"answer": self.answer, "sources": ["sql:parking_lots"]}


class _FakeReservationAgent:
    def __init__(self, done=False, state=None):
        self.updates = []
        self._done = done
        self.state = state or ReservationDetails(
            first_name="Jane", last_name="Doe", car_number="ABC123",
            period_start="9am", period_end="11am",
        )

    def update_from_message(self, message):
        self.updates.append(message)

    def next_question(self):
        return None if self._done else "Could you tell me your first name?"

    def summary(self):
        return "Name: Jane Doe\nCar number: ABC123"

    def reset(self):
        pass


class _FakePIIFilter:
    def scan(self, text):
        if "4111111111111111" in text:
            return [{"entity_type": "CREDIT_CARD", "start": 0, "end": 16, "score": 0.9}]
        return []

    def redact(self, text):
        return text, []


class _FakeAdminAgent:
    def __init__(self):
        self.escalated = []
        self._store = {}
        self._counter = 0

    def escalate(self, **kwargs):
        self._counter += 1
        request_id = f"req-{self._counter}"
        request = ReservationRequest(id=request_id, status=RequestStatus.PENDING, **kwargs)
        self._store[request_id] = request
        self.escalated.append(request)
        return request

    def get_decision(self, request_id):
        return self._store.get(request_id)

    def resolve(self, request_id, approved, reason=None):
        req = self._store[request_id]
        req.status = RequestStatus.APPROVED if approved else RequestStatus.REFUSED
        req.decision_reason = reason


def _make_bot(**overrides):
    defaults = dict(
        rag=_FakeRag(), reservation_agent=_FakeReservationAgent(),
        pii_filter=_FakePIIFilter(), admin_agent=_FakeAdminAgent(),
        retriever=object(), skip_sql_seed=True,
    )
    defaults.update(overrides)
    return ParkingChatbot(**defaults)


def test_blocks_unsafe_input_outside_reservation_mode():
    bot = _make_bot()
    response = bot.handle_message("here is my card 4111111111111111")
    assert "safety" in response.lower()


def test_static_info_intent_routes_to_answer_static():
    bot = _make_bot(rag=_FakeRag(intent="static_info", answer="Downtown opens at 6am."))
    response = bot.handle_message("When does downtown garage open?")
    assert "6am" in response


def test_reservation_intent_switches_mode_and_asks_question():
    bot = _make_bot(rag=_FakeRag(intent="reservation"))
    response = bot.handle_message("I'd like to book a spot")
    assert bot.mode == "reservation"
    assert "name" in response.lower()


def test_reservation_completion_escalates_to_admin_agent():
    admin_agent = _FakeAdminAgent()
    bot = _make_bot(reservation_agent=_FakeReservationAgent(done=True), admin_agent=admin_agent)
    bot.mode = "reservation"

    response = bot.handle_message("Jane Doe ABC123 9am-11am")

    assert bot.mode == "qa"
    assert len(admin_agent.escalated) == 1
    assert bot.pending_request_id == admin_agent.escalated[0].id
    assert admin_agent.escalated[0].id in response
    assert "administrator" in response.lower()


def test_status_check_reports_pending_decision():
    admin_agent = _FakeAdminAgent()
    bot = _make_bot(rag=_FakeRag(intent="status_check"), admin_agent=admin_agent)
    bot.pending_request_id = admin_agent.escalate(
        first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am",
    ).id

    response = bot.handle_message("What's the status of my reservation?")
    assert "pending" in response.lower()


def test_status_check_reports_approved_decision():
    admin_agent = _FakeAdminAgent()
    bot = _make_bot(rag=_FakeRag(intent="status_check"), admin_agent=admin_agent)
    request = admin_agent.escalate(
        first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am",
    )
    admin_agent.resolve(request.id, approved=True, reason="slot confirmed")
    bot.pending_request_id = request.id

    response = bot.handle_message("Any update on my reservation?")
    assert "approved" in response.lower()
    assert "slot confirmed" in response