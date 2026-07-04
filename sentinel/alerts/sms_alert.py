"""
SMS alerts via the Twilio REST API, called directly with `requests` rather
than the Twilio SDK. This keeps the dependency footprint small and makes
the request/response cycle explicit and easy to audit.

As with the other channels, missing credentials trigger a dry-run log
instead of an exception.
"""

from __future__ import annotations

import requests

from sentinel.settings import settings

REQUEST_TIMEOUT_SECONDS = 10
TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


def send_sms(body: str) -> bool:
    required = (
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.twilio_from_number,
        settings.alert_sms_to,
    )
    if not all(required):
        print(f"[sms-alert:dry-run] {body}")
        return False

    url = f"{TWILIO_API_BASE}/Accounts/{settings.twilio_account_sid}/Messages.json"
    response = requests.post(
        url,
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        data={
            "From": settings.twilio_from_number,
            "To": settings.alert_sms_to,
            "Body": body,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return True
