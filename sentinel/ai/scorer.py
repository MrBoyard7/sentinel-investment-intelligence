"""
AI scoring.

`score_item()` is the single entry point the pipeline calls. It always
returns a ScoredItem, using one of two strategies:

  1. Real mode: calls the OpenAI API with a JSON-only prompt (see
     sentinel/ai/prompts.py) and parses the structured response.
  2. Fallback / demo mode: a transparent, deterministic heuristic scorer
     that requires no API key and no network access. This keeps the
     pipeline fully runnable for review purposes, and also acts as a
     safety net in production if the OpenAI call fails or times out -
     Sentinel should degrade gracefully, not silently drop an item.

Both paths return the exact same data shape, so nothing downstream
(storage, dashboard, alerts) needs to know or care which one ran.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from sentinel.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from sentinel.collectors.base import RawItem
from sentinel.relevance import RelevanceMatch
from sentinel.settings import settings

VALID_SENTIMENTS = {"Positive", "Negative", "Neutral"}


@dataclass
class ScoredItem:
    """A RawItem enriched with the AI's (or heuristic's) analysis."""

    source_id: str
    source_name: str
    category: str
    title: str
    url: str
    published_at: str
    score: int
    sentiment: str
    summary: str
    why_it_matters: str
    recommended_action: str
    scoring_method: str  # "openai" or "heuristic-fallback", kept for transparency

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def score_item(
    item: RawItem, match: RelevanceMatch, watchlist: dict[str, Any]
) -> ScoredItem:
    if settings.demo_mode or not settings.openai_api_key:
        return _score_heuristic(item, match)

    try:
        return _score_with_openai(item, match, watchlist)
    except Exception as exc:  # noqa: BLE001 - never let a scoring error drop an item
        print(f"[scorer] OpenAI scoring failed ({exc}); using heuristic fallback.")
        return _score_heuristic(item, match)


def _score_with_openai(
    item: RawItem, match: RelevanceMatch, watchlist: dict[str, Any]
) -> ScoredItem:
    from openai import OpenAI  # imported lazily so demo mode never requires the package

    client = OpenAI(api_key=settings.openai_api_key)
    user_prompt = build_user_prompt(item, match, watchlist.get("theme", {}))

    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    payload = json.loads(response.choices[0].message.content)
    return _build_scored_item(item, payload, scoring_method="openai")


def _score_heuristic(item: RawItem, match: RelevanceMatch) -> ScoredItem:
    """
    Deterministic, offline scoring used in demo mode and as a safety-net
    fallback. This is intentionally simple: it exists to keep the pipeline
    fully functional without an API key, not to replace real LLM judgment.
    """
    haystack = f"{item.title} {item.content}".lower()

    score = 1
    score += min(len(match.matched_keywords), 2)
    if match.matched_companies:
        score += 1
    if match.matched_agency:
        score += 1
    score = max(1, min(5, score))

    negative_signals = (
        "lawsuit",
        "ban",
        "delay",
        "reject",
        "violation",
        "penalty",
        "halt",
    )
    positive_signals = (
        "approve",
        "grant",
        "funding",
        "award",
        "expansion",
        "permit issued",
    )

    if any(term in haystack for term in negative_signals):
        sentiment = "Negative"
    elif any(term in haystack for term in positive_signals):
        sentiment = "Positive"
    else:
        sentiment = "Neutral"

    summary = item.title if len(item.title) <= 200 else f"{item.title[:197]}..."
    why_it_matters = (
        "Matches watchlisted "
        + ", ".join(
            filter(
                None,
                [
                    "keywords" if match.matched_keywords else None,
                    "companies" if match.matched_companies else None,
                    "agency" if match.matched_agency else None,
                ],
            )
        )
        or "General industry development"
    )
    recommended_action = (
        "Flag for analyst review" if score >= 4 else "Monitor; no action needed"
    )

    payload = {
        "score": score,
        "sentiment": sentiment,
        "category": item.category,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "recommended_action": recommended_action,
    }
    return _build_scored_item(item, payload, scoring_method="heuristic-fallback")


def _build_scored_item(
    item: RawItem, payload: dict[str, Any], scoring_method: str
) -> ScoredItem:
    score = int(payload.get("score", 1))
    score = max(1, min(5, score))

    sentiment = payload.get("sentiment", "Neutral")
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "Neutral"

    return ScoredItem(
        source_id=item.source_id,
        source_name=item.source_name,
        category=payload.get("category", item.category),
        title=item.title,
        url=item.url,
        published_at=item.published_at,
        score=score,
        sentiment=sentiment,
        summary=payload.get("summary", item.title),
        why_it_matters=payload.get("why_it_matters", ""),
        recommended_action=payload.get("recommended_action", ""),
        scoring_method=scoring_method,
    )
