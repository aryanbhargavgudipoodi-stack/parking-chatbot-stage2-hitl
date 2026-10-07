from admin_agent import store
from admin_agent.agent import AdminAgent
from admin_agent.models import RequestStatus


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def invoke(self, _messages):
        return _FakeMessage("A new reservation needs your approval.")


class _FakeNotifier:
    def __init__(self):
        self.sent = []

    def notify(self, request, message):
        self.sent.append((request, message))


def _make_agent(tmp_path, notifier=None):
    return AdminAgent(notifier=notifier or _FakeNotifier(), llm=_FakeLLM(), db_path=str(tmp_path / "admin.db"))


def test_escalate_creates_request_and_notifies(tmp_path):
    notifier = _FakeNotifier()
    agent = _make_agent(tmp_path, notifier)

    request = agent.escalate(
        first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am",
    )

    assert request.status == RequestStatus.PENDING
    assert len(notifier.sent) == 1
    assert notifier.sent[0][0].id == request.id
    assert "approval" in notifier.sent[0][1].lower()


def test_get_decision_reflects_store_updates(tmp_path):
    agent = _make_agent(tmp_path)
    request = agent.escalate(
        first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am",
    )
    assert agent.get_decision(request.id).status == RequestStatus.PENDING

    store.set_decision(request.id, approved=True, db_path=agent.db_path)
    assert agent.get_decision(request.id).status == RequestStatus.APPROVED


def test_notification_failure_does_not_prevent_escalation(tmp_path):
    class _BrokenNotifier:
        def notify(self, request, message):
            raise RuntimeError("smtp down")

    agent = AdminAgent(notifier=_BrokenNotifier(), llm=_FakeLLM(), db_path=str(tmp_path / "admin.db"))
    request = agent.escalate(
        first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am",
    )
    assert agent.get_decision(request.id) is not None  # durably stored despite notify() failing


def test_tools_approve_requests(tmp_path):
    agent = _make_agent(tmp_path)
    request = agent.escalate(
        first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am",
    )

    tools = {t.name: t for t in agent._build_tools()}
    result = tools["approve_request"].invoke({"request_id": request.id, "reason": "ok"})

    assert "approved" in result.lower()
    assert agent.get_decision(request.id).status == RequestStatus.APPROVED