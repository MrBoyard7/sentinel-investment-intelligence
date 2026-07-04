from sentinel.collectors.base import RawItem
from sentinel.relevance import RelevanceFilter

WATCHLIST = {
    "keywords": ["critical minerals", "lithium"],
    "companies": [{"name": "MP Materials", "ticker": "MP"}],
    "agencies": ["environmental protection agency"],
}


def make_item(title="", content="", source_name="Some Source"):
    return RawItem(
        source_id="test-source",
        source_name=source_name,
        category="Test",
        title=title,
        url="https://example.com/item",
        published_at="2026-01-01T00:00:00+00:00",
        content=content,
    )


def test_matches_on_keyword():
    filt = RelevanceFilter(WATCHLIST)
    match = filt.evaluate(make_item(title="New lithium mine approved"))
    assert match.is_relevant
    assert "lithium" in match.matched_keywords


def test_matches_on_company_name():
    filt = RelevanceFilter(WATCHLIST)
    match = filt.evaluate(make_item(title="MP Materials announces expansion"))
    assert match.is_relevant
    assert "MP Materials" in match.matched_companies


def test_matches_on_ticker():
    filt = RelevanceFilter(WATCHLIST)
    match = filt.evaluate(make_item(title="Shares of MP climb after announcement"))
    assert match.is_relevant


def test_matches_on_agency_source():
    filt = RelevanceFilter(WATCHLIST)
    match = filt.evaluate(
        make_item(title="Routine notice", source_name="Environmental Protection Agency")
    )
    assert match.is_relevant
    assert match.matched_agency


def test_no_match_returns_not_relevant():
    filt = RelevanceFilter(WATCHLIST)
    match = filt.evaluate(make_item(title="City council approves new park bench"))
    assert not match.is_relevant
    assert match.matched_keywords == []
    assert match.matched_companies == []
    assert not match.matched_agency


def test_filter_only_returns_relevant_items():
    filt = RelevanceFilter(WATCHLIST)
    items = [
        make_item(title="Lithium project approved"),
        make_item(title="Unrelated local news story"),
    ]
    results = filt.filter(items)
    assert len(results) == 1
    assert results[0][0].title == "Lithium project approved"
