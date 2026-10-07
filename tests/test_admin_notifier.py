import logging

from admin_agent.models import ReservationRequest, RequestStatus
from admin_agent.notifier import ConsoleNotifier, EmailNotifier, SlackNotifier, get_notifier


def _sample_request():
    return ReservationRequest(
        id="req-1", first_name="Jane", last_name="Doe", car_number="ABC123",
        period_start="9am", period_end="11am", status=RequestStatus.PENDING,
    )


def test_console_notifier_logs_without_raising(caplog):
    caplog.set_level(logging.INFO)
    ConsoleNotifier().notify(_sample_request(), "A new reservation request needs approval.")
    assert any("req-1" in r.message for r in caplog.records)


def test_slack_notifier_posts_webhook(monkeypatch):
    calls = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def _fake_post(url, json=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        return _FakeResponse()

    monkeypatch.setattr("admin_agent.notifier.requests.post", _fake_post)

    SlackNotifier(webhook_url="https://hooks.slack.test/abc").notify(_sample_request(), "hello admin")

    assert calls["url"] == "https://hooks.slack.test/abc"
    assert calls["json"]["text"] == "hello admin"


def test_email_notifier_sends_via_smtp(monkeypatch):
    sent = {}

    class _FakeSMTP:
        def __init__(self, host, port):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def sendmail(self, from_addr, to_addrs, msg):
            sent["sendmail"] = (from_addr, to_addrs)

    monkeypatch.setattr("admin_agent.notifier.smtplib.SMTP", _FakeSMTP)

    notifier = EmailNotifier(
        smtp_host="smtp.test.com", smtp_port=587, smtp_user="bot@test.com",
        smtp_password="secret", admin_email="admin@test.com",
    )
    notifier.notify(_sample_request(), "hello")

    assert sent["host"] == "smtp.test.com"
    assert sent["login"] == ("bot@test.com", "secret")
    assert sent["sendmail"][1] == ["admin@test.com"]


def test_get_notifier_defaults_to_console(monkeypatch):
    monkeypatch.delenv("ADMIN_NOTIFICATION_CHANNEL", raising=False)
    assert isinstance(get_notifier(), ConsoleNotifier)