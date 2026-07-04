from sentinel.ai.scorer import score_item
from sentinel.collectors.base import RawItem
from sentinel.relevance import RelevanceFilter

WATCHLIST = {
    "theme": {"name": "Critical Minerals & Mining"},
    "keywords": ["critical minerals", "lithium", "permit"],
    "companies": [{"name": "MP Materials", "ticker": "MP"}],
    "agencies": ["department of the interior"],
}


def make_item(title, content=""):
    return RawItem(
        source_id="test-source",
        source_name="Department of the Interior",
        category="Government / Regulatory",
        title=title,
        url=f"https://example.com/{abs(hash(title))}",
        published_at="2026-01-01T00:00:00+00:00",
        content=content,
    )


def test_heuristic_score_within_bounds():
    item = make_item("Interior approves critical minerals permit for lithium project")
    match = RelevanceFilter(WATCHLIST).evaluate(item)
    scored = score_item(item, match, WATCHLIST)
    assert 1 <= scored.score <= 5
    assert scored.sentiment in {"Positive", "Negative", "Neutral"}
    assert scored.scoring_method == "heuristic-fallback"


def test_heuristic_detects_negative_signal():
    item = make_item("Lithium project halted after permit violation")
    match = RelevanceFilter(WATCHLIST).evaluate(item)
    scored = score_item(item, match, WATCHLIST)
    assert scored.sentiment == "Negative"


def test_heuristic_detects_positive_signal():
    item = make_item("Regulator grants critical minerals permit approval")
    match = RelevanceFilter(WATCHLIST).evaluate(item)
    scored = score_item(item, match, WATCHLIST)
    assert scored.sentiment == "Positive"


def test_more_matches_increase_score():
    weak_item = make_item("Minor procedural notice")
    strong_item = make_item(
        "Interior approves critical minerals permit for MP Materials lithium project"
    )
    weak_match = RelevanceFilter(WATCHLIST).evaluate(weak_item)
    strong_match = RelevanceFilter(WATCHLIST).evaluate(strong_item)

    weak_scored = score_item(weak_item, weak_match, WATCHLIST)
    strong_scored = score_item(strong_item, strong_match, WATCHLIST)

    assert strong_scored.score >= weak_scored.score
