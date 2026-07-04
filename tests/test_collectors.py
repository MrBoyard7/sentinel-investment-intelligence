from sentinel.collectors import build_collector


def test_rss_collector_demo_mode_loads_fixture():
    source_config = {
        "id": "federal_register",
        "name": "Federal Register",
        "type": "rss",
        "category": "Government / Regulatory",
        "url": "https://example.com/rss",
    }
    collector = build_collector(source_config)
    items = collector.collect()

    assert len(items) > 0
    assert all(item.source_id == "federal_register" for item in items)
    assert all(item.title for item in items)


def test_scrape_collector_demo_mode_loads_fixture():
    source_config = {
        "id": "whitehouse_actions",
        "name": "White House Presidential Actions",
        "type": "scrape",
        "category": "Policy",
        "url": "https://example.com",
        "list_selector": "article",
        "title_selector": "h2 a",
    }
    collector = build_collector(source_config)
    items = collector.collect()

    assert len(items) > 0
    assert all(item.source_id == "whitehouse_actions" for item in items)


def test_unknown_source_type_raises():
    import pytest

    with pytest.raises(ValueError):
        build_collector({"id": "bad", "name": "Bad Source", "type": "carrier-pigeon"})


def test_missing_fixture_returns_empty_list():
    source_config = {
        "id": "source-with-no-fixture",
        "name": "Nonexistent Source",
        "type": "rss",
        "category": "Test",
        "url": "https://example.com/rss",
    }
    collector = build_collector(source_config)
    assert collector.collect() == []
