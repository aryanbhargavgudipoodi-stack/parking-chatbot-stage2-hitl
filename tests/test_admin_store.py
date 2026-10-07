from admin_agent import store
from admin_agent.models import RequestStatus


def test_create_and_get_request(tmp_path):
    db_path = str(tmp_path / "admin.db")
    store.init_db(db_path)
    req = store.create_request("Jane", "Doe", "ABC123", "9am", "11am", db_path=db_path)
    fetched = store.get_request(req.id, db_path=db_path)
    assert fetched.first_name == "Jane"
    assert fetched.status == RequestStatus.PENDING


def test_set_decision_updates_status(tmp_path):
    db_path = str(tmp_path / "admin.db")
    store.init_db(db_path)
    req = store.create_request("Jane", "Doe", "ABC123", "9am", "11am", db_path=db_path)
    updated = store.set_decision(req.id, approved=True, reason="slot available", db_path=db_path)
    assert updated.status == RequestStatus.APPROVED
    assert updated.decision_reason == "slot available"


def test_list_requests_filters_by_status(tmp_path):
    db_path = str(tmp_path / "admin.db")
    store.init_db(db_path)
    r1 = store.create_request("Jane", "Doe", "ABC123", "9am", "11am", db_path=db_path)
    r2 = store.create_request("John", "Smith", "XYZ999", "1pm", "3pm", db_path=db_path)
    store.set_decision(r1.id, approved=True, db_path=db_path)

    pending = store.list_requests(RequestStatus.PENDING, db_path=db_path)
    assert [r.id for r in pending] == [r2.id]


def test_set_decision_on_missing_id_returns_none(tmp_path):
    db_path = str(tmp_path / "admin.db")
    store.init_db(db_path)
    assert store.set_decision("does-not-exist", approved=True, db_path=db_path) is None