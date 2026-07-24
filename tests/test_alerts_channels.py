from types import SimpleNamespace

from sentinel.alerts import email_alert, slack_alert, sms_alert

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def test_send_email_dry_run_when_not_configured(monkeypatch, capsys):
    fake_settings = SimpleNamespace(
        smtp_host="",
        alert_email_from="",
        alert_email_to="",
        smtp_port=587,
        smtp_username="",
    )
    monkeypatch.setattr(email_alert, "settings", fake_settings)

    result = email_alert.send_email("Subject", "<p>Body</p>", "Body text")

    assert result is False
    assert "email-alert:dry-run" in capsys.readouterr().out


class _FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.starttls_called = False
        self.login_args = None
        self.sendmail_args = None
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self):
        self.starttls_called = True

    def login(self, username, password):
        self.login_args = (username, password)

    def sendmail(self, from_addr, to_addr, message):
        self.sendmail_args = (from_addr, to_addr, message)


def test_send_email_sends_via_smtp_when_configured(monkeypatch):
    _FakeSMTP.instances.clear()
    fake_settings = SimpleNamespace(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user@example.com",
        smtp_password="secret",
        alert_email_from="alerts@example.com",
        alert_email_to="analyst@example.com",
    )
    monkeypatch.setattr(email_alert, "settings", fake_settings)
    monkeypatch.setattr(email_alert.smtplib, "SMTP", _FakeSMTP)

    result = email_alert.send_email("Subject", "<p>Body</p>", "Body text")

    assert result is True
    server = _FakeSMTP.instances[-1]
    assert server.starttls_called is True
    assert server.login_args == ("user@example.com", "secret")
    assert server.sendmail_args[0] == "alerts@example.com"
    assert server.sendmail_args[1] == "analyst@example.com"


def test_send_email_skips_login_without_username(monkeypatch):
    _FakeSMTP.instances.clear()
    fake_settings = SimpleNamespace(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        alert_email_from="alerts@example.com",
        alert_email_to="analyst@example.com",
    )
    monkeypatch.setattr(email_alert, "settings", fake_settings)
    monkeypatch.setattr(email_alert.smtplib, "SMTP", _FakeSMTP)

    email_alert.send_email("Subject", "<p>Body</p>")

    assert _FakeSMTP.instances[-1].login_args is None


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------


def test_send_slack_message_dry_run_when_not_configured(monkeypatch, capsys):
    monkeypatch.setattr(slack_alert, "settings", SimpleNamespace(slack_webhook_url=""))

    result = slack_alert.send_slack_message("hello")

    assert result is False
    assert "slack-alert:dry-run" in capsys.readouterr().out


def test_send_slack_message_posts_when_configured(monkeypatch):
    fake_settings = SimpleNamespace(slack_webhook_url="https://hooks.slack.test/abc")
    monkeypatch.setattr(slack_alert, "settings", fake_settings)

    calls = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        calls["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(slack_alert.requests, "post", fake_post)

    result = slack_alert.send_slack_message("hello world")

    assert result is True
    assert calls["url"] == "https://hooks.slack.test/abc"
    assert calls["json"] == {"text": "hello world"}


# ---------------------------------------------------------------------------
# SMS
# ---------------------------------------------------------------------------


def test_send_sms_dry_run_when_not_fully_configured(monkeypatch, capsys):
    fake_settings = SimpleNamespace(
        twilio_account_sid="",
        twilio_auth_token="",
        twilio_from_number="",
        alert_sms_to="",
    )
    monkeypatch.setattr(sms_alert, "settings", fake_settings)

    result = sms_alert.send_sms("hello")

    assert result is False
    assert "sms-alert:dry-run" in capsys.readouterr().out


def test_send_sms_posts_to_twilio_when_configured(monkeypatch):
    fake_settings = SimpleNamespace(
        twilio_account_sid="ACxxxx",
        twilio_auth_token="secret-token",
        twilio_from_number="+15550000000",
        alert_sms_to="+15551234567",
    )
    monkeypatch.setattr(sms_alert, "settings", fake_settings)

    calls = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, auth=None, data=None, timeout=None):
        calls["url"] = url
        calls["auth"] = auth
        calls["data"] = data
        return _FakeResponse()

    monkeypatch.setattr(sms_alert.requests, "post", fake_post)

    result = sms_alert.send_sms("Sentinel alert body")

    assert result is True
    assert "ACxxxx" in calls["url"]
    assert calls["auth"] == ("ACxxxx", "secret-token")
    assert calls["data"]["Body"] == "Sentinel alert body"
