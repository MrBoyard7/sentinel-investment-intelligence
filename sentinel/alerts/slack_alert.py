"""
Slack alerts via an incoming webhook URL.

Same dry-run philosophy as the other alert channels: no configured
webhook means the pipeline logs the message instead of failing.
"""

from __future__ import annotations

import requests

from sentinel.settings import settings

REQUEST_TIMEOUT_SECONDS = 10


def send_slack_message(text: str) -> bool:
    if not settings.slack_webhook_url:
        print(f"[slack-alert:dry-run] {text}")
        return False

    response = requests.post(
        settings.slack_webhook_url,
        json={"text": text},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return True
