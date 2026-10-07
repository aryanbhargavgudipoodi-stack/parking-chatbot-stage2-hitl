"""
Notification channels for alerting the administrator about a new
reservation request. Select via ADMIN_NOTIFICATION_CHANNEL:
  - "console" (default, zero config — logs the request)
  - "email"   (SMTP)
  - "slack"   (incoming webhook)
  - "rest"    (POST to an external admin-facing system)
"""
import json
import logging
import os
import smtplib
from email.mime.text import MIMEText

import requests

from admin_agent.models import ReservationRequest

logger = logging.getLogger("admin_notifier")


class AdminNotifier:
    def notify(self, request: ReservationRequest, message: str) -> None:
        raise NotImplementedError


class ConsoleNotifier(AdminNotifier):
    """Default channel: logs the request. Always works, no config needed."""

    def notify(self, request: ReservationRequest, message: str) -> None:
        logger.info("=== ADMIN NOTIFICATION (console channel) ===")
        logger.info("%s", message)
        logger.info("Reservation request id: %s", request.id)


class EmailNotifier(AdminNotifier):
    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_password, admin_email, from_email=None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.admin_email = admin_email
        self.from_email = from_email or smtp_user

    def notify(self, request: ReservationRequest, message: str) -> None:
        email = MIMEText(message)
        email["Subject"] = f"[Parking Chatbot] New reservation request {request.id}"
        email["From"] = self.from_email
        email["To"] = self.admin_email

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, [self.admin_email], email.as_string())


class SlackNotifier(AdminNotifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def notify(self, request: ReservationRequest, message: str) -> None:
        response = requests.post(self.webhook_url, json={"text": message}, timeout=10)
        response.raise_for_status()


class RestAPINotifier(AdminNotifier):
    """POSTs the request to an external admin-facing REST endpoint."""

    def __init__(self, endpoint_url: str, api_key: str = None):
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    def notify(self, request: ReservationRequest, message: str) -> None:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {"request": json.loads(request.model_dump_json()), "message": message}
        response = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()


def get_notifier() -> AdminNotifier:
    channel = os.getenv("ADMIN_NOTIFICATION_CHANNEL", "console")

    if channel == "email":
        return EmailNotifier(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", 587)),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            admin_email=os.getenv("ADMIN_EMAIL", ""),
        )
    if channel == "slack":
        return SlackNotifier(webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""))
    if channel == "rest":
        return RestAPINotifier(
            endpoint_url=os.getenv("ADMIN_REST_ENDPOINT", ""),
            api_key=os.getenv("ADMIN_REST_API_KEY"),
        )
    return ConsoleNotifier()