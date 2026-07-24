import time
from types import SimpleNamespace

from sentinel.collectors import base as base_module
from sentinel.collectors.base import RawItem
from sentinel.collectors.rss_collector import RSSCollector
from sentinel.collectors.web_scraper import WebScraperCollector

# ---------------------------------------------------------------------------
# RawItem / BaseCollector
# ---------------------------------------------------------------------------


def test_raw_item_to_dict():
    item = RawItem(
        source_id="s",
        source_name="Source",
        category="Category",
        title="Title",
        url="https://example.com",
        published_at="2026-01-01T00:00:00+00:00",
        content="content",
    )
    d = item.to_dict()
    assert isinstance(d, dict)
    assert d["title"] == "Title"


def test_collect_falls_back_to_demo_on_live_exception(monkeypatch):
    # `settings` is a frozen dataclass singleton: swap the module-level name
    # for a plain mutable stand-in rather than mutating it in place.
    monkeypatch.setattr(base_module, "settings", SimpleNamespace(demo_mode=False))
    source_config = {
        "id": "federal_register",
        "name": "Federal Register",
        "type": "rss",
        "category": "Government / Regulatory",
        "url": "https://example.com/rss",
    }
    collector = RSSCollector(source_config)
    monkeypatch.setattr(
        collector,
        "_collect_live",
        lambda: (_ for _ in ()).throw(RuntimeError("network down")),
    )

    items = collector.collect()

    # Falls back to the federal_register fixture instead of raising.
    assert len(items) > 0
    assert all(isinstance(i, RawItem) for i in items)


def test_collect_uses_live_path_when_demo_mode_disabled(monkeypatch):
    monkeypatch.setattr(base_module, "settings", SimpleNamespace(demo_mode=False))
    source_config = {
        "id": "x",
        "name": "X",
        "type": "rss",
        "category": "Test",
        "url": "https://example.com",
    }
    collector = RSSCollector(source_config)

    sentinel_items = [
        RawItem(
            source_id="x",
            source_name="X",
            category="Test",
            title="Live item",
            url="https://example.com/live",
            published_at="2026-01-01T00:00:00+00:00",
            content="",
        )
    ]
    monkeypatch.setattr(collector, "_collect_live", lambda: sentinel_items)

    items = collector.collect()

    assert items == sentinel_items


# ---------------------------------------------------------------------------
# RSSCollector._collect_live
# ---------------------------------------------------------------------------


class _FakeEntry(dict):
    """Mimics feedparser's FeedParserDict: supports both dict and attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class _FakeParsedFeed:
    def __init__(self, entries):
        self.entries = entries


def test_rss_collect_live_extracts_summary_and_published_parsed(monkeypatch):
    published = time.struct_time((2026, 6, 12, 14, 0, 0, 0, 0, 0))
    entry = _FakeEntry(
        title="Notice of Proposed Rulemaking",
        link="https://example.com/notice",
        summary="A short summary.",
        published_parsed=published,
    )
    fake_feed = _FakeParsedFeed([entry])
    monkeypatch.setattr(
        "sentinel.collectors.rss_collector.feedparser.parse", lambda url: fake_feed
    )

    source_config = {
        "id": "federal_register",
        "name": "Federal Register",
        "type": "rss",
        "category": "Government / Regulatory",
        "url": "https://example.com/rss",
    }
    collector = RSSCollector(source_config)
    items = collector._collect_live()

    assert len(items) == 1
    assert items[0].title == "Notice of Proposed Rulemaking"
    assert items[0].content == "A short summary."
    assert items[0].published_at.startswith("2026-06-12")


def test_rss_collect_live_falls_back_to_content_field(monkeypatch):
    entry = _FakeEntry(
        title="No summary here",
        link="https://example.com/x",
        content=[{"value": "Body from content field"}],
    )
    fake_feed = _FakeParsedFeed([entry])
    monkeypatch.setattr(
        "sentinel.collectors.rss_collector.feedparser.parse", lambda url: fake_feed
    )

    source_config = {
        "id": "x",
        "name": "X",
        "type": "rss",
        "category": "Test",
        "url": "https://example.com",
    }
    items = RSSCollector(source_config)._collect_live()

    assert items[0].content == "Body from content field"


def test_rss_collect_live_handles_missing_dates_and_content(monkeypatch):
    entry = _FakeEntry(title="Bare entry", link="https://example.com/bare")
    fake_feed = _FakeParsedFeed([entry])
    monkeypatch.setattr(
        "sentinel.collectors.rss_collector.feedparser.parse", lambda url: fake_feed
    )

    source_config = {
        "id": "x",
        "name": "X",
        "type": "rss",
        "category": "Test",
        "url": "https://example.com",
    }
    items = RSSCollector(source_config)._collect_live()

    assert items[0].content == ""
    assert items[0].published_at  # falls back to "now", but is never empty


# ---------------------------------------------------------------------------
# WebScraperCollector._collect_live
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html><body>
  <article>
    <h2><a href="/news/1">First announcement</a></h2>
    <time datetime="2026-01-01T00:00:00Z">Jan 1</time>
  </article>
  <article>
    <h2><a href="https://other.example.com/news/2">Second announcement</a></h2>
    <time datetime="2026-01-02T00:00:00Z">Jan 2</time>
  </article>
  <article>
    <h2>No link here</h2>
  </article>
</body></html>
"""


class _FakeHTTPResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_web_scraper_collect_live_extracts_items_and_absolutizes_links(monkeypatch):
    monkeypatch.setattr(
        "sentinel.collectors.web_scraper.requests.get",
        lambda url, headers=None, timeout=None: _FakeHTTPResponse(SAMPLE_HTML),
    )

    source_config = {
        "id": "whitehouse_actions",
        "name": "White House Presidential Actions",
        "type": "scrape",
        "category": "Policy",
        "url": "https://example.com/briefing-room/",
        "list_selector": "article",
        "title_selector": "h2 a",
        "link_selector": "h2 a",
        "date_selector": "time",
    }
    collector = WebScraperCollector(source_config)
    items = collector._collect_live()

    # The third <article> has no <a> and should be skipped.
    assert len(items) == 2

    assert items[0].title == "First announcement"
    assert items[0].url == "https://example.com/news/1"  # relative href absolutized

    assert items[1].title == "Second announcement"
    assert (
        items[1].url == "https://other.example.com/news/2"
    )  # already absolute, unchanged


def test_web_scraper_collect_live_without_date_selector_uses_now(monkeypatch):
    monkeypatch.setattr(
        "sentinel.collectors.web_scraper.requests.get",
        lambda url, headers=None, timeout=None: _FakeHTTPResponse(SAMPLE_HTML),
    )

    source_config = {
        "id": "x",
        "name": "X",
        "type": "scrape",
        "category": "Test",
        "url": "https://example.com/",
        "list_selector": "article",
        "title_selector": "h2 a",
    }
    items = WebScraperCollector(source_config)._collect_live()

    assert len(items) == 2
    assert items[0].published_at  # fell back to "now", never empty
