from types import SimpleNamespace

import pytest

from sentinel.cli import main


def test_run_command_invokes_pipeline_and_prints_json(monkeypatch, capsys):
    monkeypatch.setattr("sentinel.pipeline.run_once", lambda: {"items_stored": 3})

    exit_code = main(["run"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"items_stored": 3' in out


def test_daily_digest_command(monkeypatch, capsys):
    monkeypatch.setattr(
        "sentinel.pipeline.run_daily_digest", lambda: {"items_in_digest": 2}
    )

    exit_code = main(["daily-digest"])

    assert exit_code == 0
    assert '"items_in_digest": 2' in capsys.readouterr().out


def test_weekly_digest_command(monkeypatch, capsys):
    monkeypatch.setattr(
        "sentinel.pipeline.run_weekly_digest", lambda: {"items_in_digest": 5}
    )

    exit_code = main(["weekly-digest"])

    assert exit_code == 0
    assert '"items_in_digest": 5' in capsys.readouterr().out


def test_schedule_command_passes_interval_through(monkeypatch):
    captured = {}

    def fake_run_scheduler(scan_interval_minutes):
        captured["interval"] = scan_interval_minutes

    monkeypatch.setattr("sentinel.pipeline.run_scheduler", fake_run_scheduler)

    exit_code = main(["schedule", "--interval-minutes", "15"])

    assert exit_code == 0
    assert captured["interval"] == 15


def test_schedule_command_defaults_to_30_minutes(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "sentinel.pipeline.run_scheduler",
        lambda scan_interval_minutes: captured.setdefault(
            "interval", scan_interval_minutes
        ),
    )

    main(["schedule"])

    assert captured["interval"] == 30


def test_dashboard_command_starts_flask_app_without_a_real_server(monkeypatch):
    run_calls = {}

    class _FakeApp:
        def run(self, host=None, port=None, debug=None):
            run_calls["host"] = host
            run_calls["port"] = port
            run_calls["debug"] = debug

    monkeypatch.setattr("sentinel.dashboard.app.create_app", lambda: _FakeApp())
    monkeypatch.setattr(
        "sentinel.settings.settings",
        SimpleNamespace(dashboard_host="127.0.0.1", dashboard_port=5000),
    )

    exit_code = main(["dashboard"])

    assert exit_code == 0
    assert run_calls == {"host": "127.0.0.1", "port": 5000, "debug": False}


def test_seed_demo_command_in_demo_mode_prints_no_warning(monkeypatch, capsys):
    monkeypatch.setattr("sentinel.settings.settings", SimpleNamespace(demo_mode=True))
    monkeypatch.setattr("sentinel.pipeline.run_once", lambda: {"items_stored": 14})

    exit_code = main(["seed-demo"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Warning" not in out
    assert "Demo pipeline run complete" in out
    assert "Start the dashboard" in out


def test_seed_demo_command_warns_when_demo_mode_disabled(monkeypatch, capsys):
    monkeypatch.setattr("sentinel.settings.settings", SimpleNamespace(demo_mode=False))
    monkeypatch.setattr("sentinel.pipeline.run_once", lambda: {"items_stored": 0})

    main(["seed-demo"])

    assert "Warning: DEMO_MODE is not enabled" in capsys.readouterr().out


def test_main_requires_a_command():
    with pytest.raises(SystemExit):
        main([])
