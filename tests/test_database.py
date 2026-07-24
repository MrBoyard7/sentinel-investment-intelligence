from sqlalchemy import create_engine

from sentinel.ai.scorer import ScoredItem
from sentinel.storage import database


def _isolated_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", engine)
    database.init_db()
    return engine


def make_scored(url, score=3, sentiment="Neutral", category="Policy", source_id="src"):
    return ScoredItem(
        source_id=source_id,
        source_name="Test Source",
        category=category,
        title=f"Item at {url}",
        url=url,
        published_at="2026-01-01T00:00:00+00:00",
        score=score,
        sentiment=sentiment,
        summary="Summary",
        why_it_matters="Why",
        recommended_action="Action",
        scoring_method="heuristic-fallback",
    )


def test_insert_scored_items_deduplicates_by_url(monkeypatch):
    _isolated_engine(monkeypatch)

    first_pass = database.insert_scored_items(
        [make_scored("https://example.com/a"), make_scored("https://example.com/b")]
    )
    second_pass = database.insert_scored_items(
        [make_scored("https://example.com/a"), make_scored("https://example.com/c")]
    )

    assert len(first_pass) == 2
    assert len(second_pass) == 1  # only the new "/c" URL is inserted
    assert second_pass[0].url == "https://example.com/c"


def test_get_items_filters_by_min_score(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [
            make_scored("https://example.com/low", score=1),
            make_scored("https://example.com/high", score=5),
        ]
    )

    results = database.get_items(min_score=4)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/high"


def test_get_items_filters_by_category(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [
            make_scored("https://example.com/a", category="Policy"),
            make_scored("https://example.com/b", category="Litigation"),
        ]
    )

    results = database.get_items(category="Litigation")

    assert len(results) == 1
    assert results[0]["category"] == "Litigation"


def test_get_items_filters_by_sentiment(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [
            make_scored("https://example.com/a", sentiment="Positive"),
            make_scored("https://example.com/b", sentiment="Negative"),
        ]
    )

    results = database.get_items(sentiment="Negative")

    assert len(results) == 1
    assert results[0]["sentiment"] == "Negative"


def test_get_pending_immediate_alerts_and_mark_sent(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [
            make_scored("https://example.com/low", score=2),
            make_scored("https://example.com/high", score=5),
        ]
    )

    pending = database.get_pending_immediate_alerts(min_score=4)
    assert len(pending) == 1
    high_id = pending[0].id

    database.mark_immediate_alert_sent([high_id])

    pending_after = database.get_pending_immediate_alerts(min_score=4)
    assert pending_after == []


def test_mark_immediate_alert_sent_with_empty_list_is_a_no_op(monkeypatch):
    _isolated_engine(monkeypatch)
    # Should not raise even though there is nothing to update.
    database.mark_immediate_alert_sent([])


def test_get_items_for_digest_and_mark_included(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [make_scored("https://example.com/a"), make_scored("https://example.com/b")]
    )

    daily_pending = database.get_items_for_digest("daily")
    assert len(daily_pending) == 2

    database.mark_included_in_digest([i.id for i in daily_pending], "daily")

    assert database.get_items_for_digest("daily") == []
    # Weekly digest flag is independent of the daily one.
    assert len(database.get_items_for_digest("weekly")) == 2


def test_get_stats_aggregates_correctly(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [
            make_scored(
                "https://example.com/a",
                score=5,
                sentiment="Positive",
                category="Policy",
            ),
            make_scored(
                "https://example.com/b",
                score=2,
                sentiment="Negative",
                category="Policy",
            ),
            make_scored(
                "https://example.com/c",
                score=4,
                sentiment="Neutral",
                category="Litigation",
            ),
        ]
    )

    stats = database.get_stats()

    assert stats["total_items"] == 3
    assert stats["high_priority_items"] == 2  # scores 5 and 4 (threshold default is 4)
    assert stats["by_category"] == {"Policy": 2, "Litigation": 1}
    assert stats["by_sentiment"]["Positive"] == 1
    assert stats["by_sentiment"]["Negative"] == 1
    assert stats["by_sentiment"]["Neutral"] == 1


def test_get_stats_on_empty_database(monkeypatch):
    _isolated_engine(monkeypatch)

    stats = database.get_stats()

    assert stats["total_items"] == 0
    assert stats["high_priority_items"] == 0
