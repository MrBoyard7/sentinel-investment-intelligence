"""
Central configuration for Sentinel.

Everything that varies between a laptop demo run and a production
deployment lives here: environment variables (secrets, feature flags) and
the two YAML files that define the watchlist and the sources.

Importing this module has no side effects beyond reading files from disk,
so it is safe to import from anywhere (collectors, scorer, dashboard, CLI)
without worrying about import order or circular dependencies.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load a local .env file if present. In production this is typically
# replaced by real environment variables injected by the host platform.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DEMO_FIXTURES_DIR = DATA_DIR / "demo_fixtures"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings resolved once at import time."""

    demo_mode: bool = field(default_factory=lambda: _env_bool("DEMO_MODE", True))

    # AI scoring
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )

    # Storage
    database_path: str = field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "data/db/sentinel.sqlite3")
    )

    # Email
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 587))
    smtp_username: str = field(default_factory=lambda: os.getenv("SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    alert_email_from: str = field(
        default_factory=lambda: os.getenv("ALERT_EMAIL_FROM", "")
    )
    alert_email_to: str = field(default_factory=lambda: os.getenv("ALERT_EMAIL_TO", ""))

    # Slack
    slack_webhook_url: str = field(
        default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", "")
    )

    # SMS (Twilio REST API, called directly over HTTPS - no SDK dependency)
    twilio_account_sid: str = field(
        default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", "")
    )
    twilio_auth_token: str = field(
        default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", "")
    )
    twilio_from_number: str = field(
        default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER", "")
    )
    alert_sms_to: str = field(default_factory=lambda: os.getenv("ALERT_SMS_TO", ""))

    # Dashboard
    dashboard_host: str = field(
        default_factory=lambda: os.getenv("DASHBOARD_HOST", "127.0.0.1")
    )
    dashboard_port: int = field(
        default_factory=lambda: _env_int("DASHBOARD_PORT", 5000)
    )

    # Alerting
    immediate_alert_score: int = field(
        default_factory=lambda: _env_int("IMMEDIATE_ALERT_SCORE", 4)
    )

    @property
    def database_full_path(self) -> Path:
        path = Path(self.database_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_watchlist() -> dict[str, Any]:
    """Load config/watchlist.yaml (theme, keywords, companies, agencies)."""
    return _load_yaml(CONFIG_DIR / "watchlist.yaml")


def load_sources() -> list[dict[str, Any]]:
    """Load config/sources.yaml and return the list of source definitions."""
    data = _load_yaml(CONFIG_DIR / "sources.yaml")
    return data.get("sources", [])


settings = Settings()
