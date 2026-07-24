from sentinel.ai.prompts import build_user_prompt
from sentinel.collectors.base import RawItem
from sentinel.relevance import RelevanceMatch

ITEM = RawItem(
    source_id="federal_register",
    source_name="Federal Register",
    category="Government / Regulatory",
    title="Notice of Proposed Rulemaking on Critical Minerals",
    url="https://example.com/notice",
    published_at="2026-06-12T14:00:00+00:00",
    content="Some regulatory content about critical minerals permitting.",
)

THEME = {"name": "Critical Minerals & Mining", "description": "Tracks mining policy."}


def test_prompt_includes_matched_keywords():
    match = RelevanceMatch(
        is_relevant=True,
        matched_keywords=["critical minerals", "permit"],
        matched_companies=[],
        matched_agency=False,
    )
    prompt = build_user_prompt(ITEM, match, THEME)
    assert "Matched keywords: critical minerals, permit" in prompt
    assert "Investment theme: Critical Minerals & Mining" in prompt
    assert ITEM.title in prompt


def test_prompt_includes_matched_companies():
    match = RelevanceMatch(
        is_relevant=True,
        matched_keywords=[],
        matched_companies=["MP Materials"],
        matched_agency=False,
    )
    prompt = build_user_prompt(ITEM, match, THEME)
    assert "Matched companies: MP Materials" in prompt


def test_prompt_includes_agency_flag():
    match = RelevanceMatch(
        is_relevant=True, matched_keywords=[], matched_companies=[], matched_agency=True
    )
    prompt = build_user_prompt(ITEM, match, THEME)
    assert "watchlisted government agency" in prompt


def test_prompt_falls_back_when_no_match_signal():
    match = RelevanceMatch(
        is_relevant=True,
        matched_keywords=[],
        matched_companies=[],
        matched_agency=False,
    )
    prompt = build_user_prompt(ITEM, match, THEME)
    assert "No direct keyword match." in prompt


def test_prompt_handles_missing_theme_fields():
    match = RelevanceMatch(
        is_relevant=True,
        matched_keywords=[],
        matched_companies=[],
        matched_agency=False,
    )
    prompt = build_user_prompt(ITEM, match, {})
    assert "Investment theme: Unspecified" in prompt


def test_prompt_truncates_long_content():
    long_item = RawItem(
        source_id="x",
        source_name="X",
        category="Test",
        title="Long content item",
        url="https://example.com/long",
        published_at="2026-01-01T00:00:00+00:00",
        content="A" * 5000,
    )
    match = RelevanceMatch(
        is_relevant=True,
        matched_keywords=[],
        matched_companies=[],
        matched_agency=False,
    )
    prompt = build_user_prompt(long_item, match, THEME)
    # Content is truncated to 3000 chars in the template.
    assert "A" * 3000 in prompt
    assert "A" * 3001 not in prompt
