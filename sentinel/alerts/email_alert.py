"""
Email alerts via SMTP (stdlib smtplib - no extra dependency required).

If SMTP credentials are not configured, `send_email` runs in "dry-run"
mode: it prints what it would have sent instead of raising, so the
pipeline never crashes in a demo environment just because alerting isn't
wired up yet.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sentinel.settings import settings


def send_email(subject: str, body_html: str, body_text: str | None = None) -> bool:
    """
    Send an HTML email alert. Returns True if actually sent, False if it
    ran in dry-run mode (missing configuration).
    """
    if not (
        settings.smtp_host and settings.alert_email_from and settings.alert_email_to
    ):
        print(f"[email-alert:dry-run] Subject: {subject}\n{body_text or body_html}\n")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.alert_email_from
    message["To"] = settings.alert_email_to

    if body_text:
        message.attach(MIMEText(body_text, "plain"))
    message.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(
            settings.alert_email_from, settings.alert_email_to, message.as_string()
        )
    return True
