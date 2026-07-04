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
