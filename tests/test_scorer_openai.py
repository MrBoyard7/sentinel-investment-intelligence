import json
from types import SimpleNamespace

import pytest

from sentinel.ai import scorer as scorer_module
from sentinel.ai.scorer import ScoredItem, _build_scored_item, score_item
from sentinel.collectors.base import RawItem
from sentinel.relevance import RelevanceFilter

WATCHLIST = {
    "theme": {"name": "Critical Minerals & Mining"},
    "keywords": ["critical minerals"],
    "companies": [],
    "agencies": [],
}


def make_item(title="Critical minerals policy update"):
    return RawItem(
        source_id="federal_register",
        source_name="Federal Register",
        category="Government / Regulatory",
        title=title,
        url=f"https://example.com/{abs(hash(title))}",
        published_at="2026-01-01T00:00:00+00:00",
        content="Some content mentioning critical minerals.",
    )


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content=None, raise_exc=None):
        self._content = content
        self._raise_exc = raise_exc

    def create(self, **kwargs):
        if self._raise_exc:
            raise self._raise_exc
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, **kwargs):
        self.completions = _FakeCompletions(**kwargs)


class _FakeOpenAIClient:
    def __init__(self, api_key=None, **kwargs):
        self.api_key = api_key
        self.chat = _FakeChat(**kwargs)


@pytest.fixture
def real_mode_settings(monkeypatch):
    """Force score_item into the OpenAI code path instead of the heuristic."""
    fake_settings = SimpleNamespace(
        demo_mode=False,
        openai_api_key="fake-test-key",
        openai_model="gpt-4o-mini",
    )
    monkeypatch.setattr(scorer_module, "settings", fake_settings)
    return fake_settings


def test_score_item_uses_openai_when_configured(monkeypatch, real_mode_settings):
    payload = {
        "score": 5,
        "sentiment": "Positive",
        "category": "Policy",
        "summary": "Major supportive policy announced.",
        "why_it_matters": "Directly boosts the theme.",
        "recommended_action": "Flag for portfolio review",
    }

    def fake_openai_factory(api_key=None):
        return _FakeOpenAIClient(api_key=api_key, content=json.dumps(payload))

    monkeypatch.setattr("openai.OpenAI", fake_openai_factory)

    item = make_item()
    match = RelevanceFilter(WATCHLIST).evaluate(item)
    scored = score_item(item, match, WATCHLIST)

    assert scored.scoring_method == "openai"
    assert scored.score == 5
    assert scored.sentiment == "Positive"
    assert scored.category == "Policy"


def test_score_item_falls_back_to_heuristic_on_api_error(
    monkeypatch, real_mode_settings
):
    def fake_openai_factory(api_key=None):
        return _FakeOpenAIClient(api_key=api_key, raise_exc=RuntimeError("API is down"))

    monkeypatch.setattr("openai.OpenAI", fake_openai_factory)

    item = make_item()
    match = RelevanceFilter(WATCHLIST).evaluate(item)
    scored = score_item(item, match, WATCHLIST)

    assert scored.scoring_method == "heuristic-fallback"
    assert 1 <= scored.score <= 5


def test_score_item_falls_back_to_heuristic_on_invalid_json(
    monkeypatch, real_mode_settings
):
    def fake_openai_factory(api_key=None):
        return _FakeOpenAIClient(api_key=api_key, content="not valid json")

    monkeypatch.setattr("openai.OpenAI", fake_openai_factory)

    item = make_item()
    match = RelevanceFilter(WATCHLIST).evaluate(item)
    scored = score_item(item, match, WATCHLIST)

    assert scored.scoring_method == "heuristic-fallback"


def test_build_scored_item_clamps_out_of_range_score():
    item = make_item()
    scored_high = _build_scored_item(item, {"score": 99}, scoring_method="test")
    scored_low = _build_scored_item(item, {"score": -10}, scoring_method="test")
    assert scored_high.score == 5
    assert scored_low.score == 1


def test_build_scored_item_defaults_invalid_sentiment_to_neutral():
    item = make_item()
    scored = _build_scored_item(
        item, {"score": 3, "sentiment": "Ecstatic"}, scoring_method="test"
    )
    assert scored.sentiment == "Neutral"


def test_scored_item_to_dict_returns_plain_dict():
    scored = ScoredItem(
        source_id="s",
        source_name="Source",
        category="Category",
        title="Title",
        url="https://example.com",
        published_at="2026-01-01T00:00:00+00:00",
        score=3,
        sentiment="Neutral",
        summary="Summary",
        why_it_matters="Why",
        recommended_action="Action",
        scoring_method="heuristic-fallback",
    )
    d = scored.to_dict()
    assert isinstance(d, dict)
    assert d["score"] == 3
    assert d["scoring_method"] == "heuristic-fallback"
