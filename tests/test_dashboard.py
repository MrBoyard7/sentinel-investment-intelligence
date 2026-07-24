from sqlalchemy import create_engine

from sentinel.ai.scorer import ScoredItem
from sentinel.storage import database


def _isolated_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(database, "_engine", engine)
    database.init_db()
    return engine


def make_scored(url, score=3, sentiment="Neutral", category="Government / Regulatory"):
    return ScoredItem(
        source_id="federal_register",
        source_name="Federal Register",
        category=category,
        title=f"Test item {url}",
        url=url,
        published_at="2026-06-01T00:00:00+00:00",
        score=score,
        sentiment=sentiment,
        summary="A test summary.",
        why_it_matters="Because it is a test.",
        recommended_action="Monitor",
        scoring_method="heuristic-fallback",
    )


def _make_client(monkeypatch):
    _isolated_engine(monkeypatch)
    database.insert_scored_items(
        [
            make_scored("https://example.com/low", score=2, sentiment="Neutral"),
            make_scored("https://example.com/high", score=5, sentiment="Positive"),
        ]
    )

    from sentinel.dashboard.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_index_page_renders_with_items(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "SENTINEL" in html
    assert "Test item https://example.com/high" in html


def test_api_items_returns_all_items_by_default(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/api/items")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 2


def test_api_items_filters_by_min_score(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/api/items?min_score=4")

    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["url"] == "https://example.com/high"


def test_api_items_filters_by_sentiment(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/api/items?sentiment=Positive")

    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["sentiment"] == "Positive"


def test_api_stats_returns_aggregate_counts(monkeypatch):
    client = _make_client(monkeypatch)

    response = client.get("/api/stats")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total_items"] == 2
    assert payload["high_priority_items"] == 1


def test_static_assets_are_served(monkeypatch):
    client = _make_client(monkeypatch)

    css_response = client.get("/static/css/style.css")
    js_response = client.get("/static/js/dashboard.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200
