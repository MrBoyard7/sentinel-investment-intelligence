from types import SimpleNamespace

from sentinel.alerts import digest as digest_module


def make_item(**overrides):
    defaults = dict(
        id=1,
        score=3,
        sentiment="Neutral",
        category="Policy",
        title="Some development",
        source_name="Federal Register",
        summary="A summary.",
        why_it_matters="It matters because...",
        recommended_action="Monitor",
        url="https://example.com/item",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _patch_channels(monkeypatch):
    calls = {"email": [], "slack": [], "sms": []}
    monkeypatch.setattr(
        digest_module,
        "send_email",
        lambda subject, body_html, body_text=None: calls["email"].append(subject),
    )
    monkeypatch.setattr(
        digest_module, "send_slack_message", lambda text: calls["slack"].append(text)
    )
    monkeypatch.setattr(
        digest_module, "send_sms", lambda body: calls["sms"].append(body)
    )
    return calls


def test_immediate_alert_sends_email_and_slack_but_not_sms_below_5(monkeypatch):
    calls = _patch_channels(monkeypatch)
    item = make_item(score=4)

    digest_module.send_immediate_alert(item)

    assert len(calls["email"]) == 1
    assert len(calls["slack"]) == 1
    assert len(calls["sms"]) == 0


def test_immediate_alert_sends_sms_for_score_5(monkeypatch):
    calls = _patch_channels(monkeypatch)
    item = make_item(score=5, title="Critical urgent development")

    digest_module.send_immediate_alert(item)

    assert len(calls["sms"]) == 1
    assert "Critical urgent development" in calls["sms"][0]


def test_send_digest_does_nothing_for_empty_list(monkeypatch):
    calls = _patch_channels(monkeypatch)

    digest_module.send_digest([], "daily")

    assert calls["email"] == []
    assert calls["slack"] == []


def test_send_digest_sends_one_email_and_one_slack_message(monkeypatch):
    calls = _patch_channels(monkeypatch)
    items = [
        make_item(id=1, score=2, title="Low priority item"),
        make_item(id=2, score=5, title="High priority item"),
    ]

    digest_module.send_digest(items, "weekly")

    assert len(calls["email"]) == 1
    assert "Weekly Digest" in calls["email"][0]
    assert len(calls["slack"]) == 1
    assert "Weekly Digest" in calls["slack"][0]


def test_send_digest_labels_daily_correctly(monkeypatch):
    calls = _patch_channels(monkeypatch)
    items = [make_item(id=1, score=3)]

    digest_module.send_digest(items, "daily")

    assert "Daily Digest" in calls["email"][0]
