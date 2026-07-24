from sqlalchemy import create_engine

from sentinel import pipeline
from sentinel.storage import database


def test_run_once_end_to_end(monkeypatch):
    """
    Runs the full pipeline (collect -> filter -> score -> store -> alert)
    against the demo fixtures with an isolated in-memory database, so this
    test never touches the real data/db/sentinel.sqlite3 file and can be
    run repeatedly without accumulating state.
    """
    in_memory_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", in_memory_engine)

    summary = pipeline.run_once()

    assert summary["sources_scanned"] > 0
    assert summary["items_collected"] > 0
    assert summary["items_relevant"] > 0
    assert summary["items_stored"] > 0

    stored_items = database.get_items(limit=500)
    assert len(stored_items) == summary["items_stored"]
    assert all(1 <= item["score"] <= 5 for item in stored_items)


def test_run_once_is_idempotent_on_duplicate_urls(monkeypatch):
    in_memory_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", in_memory_engine)

    first_summary = pipeline.run_once()
    second_summary = pipeline.run_once()

    # The second pass collects the same fixture items again, but none
    # should be re-inserted since they are de-duplicated by URL.
    assert second_summary["items_stored"] == 0
    assert first_summary["items_stored"] > 0


def test_run_daily_digest_marks_items_and_is_idempotent(monkeypatch):
    in_memory_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", in_memory_engine)
    pipeline.run_once()  # populate the database from demo fixtures

    first_run = pipeline.run_daily_digest()
    second_run = pipeline.run_daily_digest()

    assert first_run["items_in_digest"] > 0
    # Every item was already marked as included in the first pass.
    assert second_run["items_in_digest"] == 0


def test_run_weekly_digest_marks_items_and_is_idempotent(monkeypatch):
    in_memory_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", in_memory_engine)
    pipeline.run_once()

    first_run = pipeline.run_weekly_digest()
    second_run = pipeline.run_weekly_digest()

    assert first_run["items_in_digest"] > 0
    assert second_run["items_in_digest"] == 0


def test_daily_and_weekly_digest_flags_are_independent(monkeypatch):
    in_memory_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", in_memory_engine)
    pipeline.run_once()

    pipeline.run_daily_digest()
    # Marking the daily digest done should not affect the weekly one.
    weekly_run = pipeline.run_weekly_digest()

    assert weekly_run["items_in_digest"] > 0


class _FakeBlockingScheduler:
    """Records job registrations instead of actually blocking forever."""

    instances = []

    def __init__(self):
        self.jobs = []
        self.started = False
        _FakeBlockingScheduler.instances.append(self)

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append((func, trigger, kwargs))

    def start(self):
        self.started = True


def test_run_scheduler_registers_expected_jobs(monkeypatch):
    _FakeBlockingScheduler.instances.clear()
    monkeypatch.setattr(
        "apscheduler.schedulers.blocking.BlockingScheduler", _FakeBlockingScheduler
    )

    pipeline.run_scheduler(scan_interval_minutes=15)

    scheduler = _FakeBlockingScheduler.instances[-1]
    assert scheduler.started is True
    assert len(scheduler.jobs) == 3

    job_ids = [kwargs["id"] for _, _, kwargs in scheduler.jobs]
    assert job_ids == ["scan", "daily_digest", "weekly_digest"]

    scan_func, scan_trigger, scan_kwargs = scheduler.jobs[0]
    assert scan_func is pipeline.run_once
    assert scan_trigger == "interval"
    assert scan_kwargs["minutes"] == 15
