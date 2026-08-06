"""Direct alert sinks: Slack webhook and SMTP email."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger("honeyshop.alerts")


@dataclass
class AlertConfig:
    slack_webhook: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    use_tls: bool = True

    @classmethod
    def from_env(cls) -> "AlertConfig":
        return cls(
            slack_webhook=os.environ.get("HONEYSHOP_SLACK_WEBHOOK") or None,
            smtp_host=os.environ.get("HONEYSHOP_SMTP_HOST") or None,
            smtp_port=int(os.environ.get("HONEYSHOP_SMTP_PORT", "587")),
            smtp_user=os.environ.get("HONEYSHOP_SMTP_USER") or None,
            smtp_password=os.environ.get("HONEYSHOP_SMTP_PASSWORD") or None,
            email_from=os.environ.get("HONEYSHOP_EMAIL_FROM") or None,
            email_to=os.environ.get("HONEYSHOP_EMAIL_TO") or None,
            use_tls=os.environ.get("HONEYSHOP_SMTP_TLS", "1") not in ("0", "false", "False"),
        )


class Notifier:
    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig.from_env()

    @property
    def enabled(self) -> bool:
        return bool(self.config.slack_webhook or (self.config.smtp_host and self.config.email_to))

    def send(self, title: str, body: str, severity: str = "medium") -> None:
        if not self.enabled:
            return
        if self.config.slack_webhook:
            self._slack(title, body, severity)
        if self.config.smtp_host and self.config.email_to:
            self._email(title, body, severity)

    def _slack(self, title: str, body: str, severity: str) -> None:
        color = {"high": "#ff6b6b", "medium": "#f5c16c", "low": "#3dd68c"}.get(severity, "#f5c16c")
        payload = {
            "text": f"*Honeyshop* [{severity.upper()}] {title}",
            "attachments": [{"color": color, "text": body, "mrkdwn_in": ["text"]}],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.slack_webhook,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    logger.warning("Slack webhook returned %s", resp.status)
        except urllib.error.URLError as e:
            logger.warning("Slack alert failed: %s", e)

    def _email(self, title: str, body: str, severity: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"[Honeyshop/{severity}] {title}"
        msg["From"] = self.config.email_from or self.config.smtp_user or "honeyshop@localhost"
        msg["To"] = self.config.email_to
        msg.set_content(body)
        try:
            if self.config.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=15) as s:
                    s.starttls(context=context)
                    if self.config.smtp_user and self.config.smtp_password:
                        s.login(self.config.smtp_user, self.config.smtp_password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=15) as s:
                    if self.config.smtp_user and self.config.smtp_password:
                        s.login(self.config.smtp_user, self.config.smtp_password)
                    s.send_message(msg)
        except Exception as e:
            logger.warning("Email alert failed: %s", e)
