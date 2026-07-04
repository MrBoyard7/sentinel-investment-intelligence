"""
Relevance filtering.

This is the system's first line of defense against alert fatigue and
wasted AI-scoring spend: a cheap, deterministic keyword/company/agency
match runs *before* anything reaches the (comparatively expensive) AI
scorer. Only items that pass this filter are analyzed and stored.

See docs/design-rationale.md for the full discussion of how this,
combined with the AI's own importance score and the digest/immediate
alert split, keeps false positives and alert fatigue under control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinel.collectors.base import RawItem


@dataclass
class RelevanceMatch:
    """Why an item was judged relevant, kept for auditability in the dashboard."""

    is_relevant: bool
    matched_keywords: list[str]
    matched_companies: list[str]
    matched_agency: bool


class RelevanceFilter:
    """Applies config/watchlist.yaml against collected items."""

    def __init__(self, watchlist: dict[str, Any]):
        self.keywords = [kw.lower() for kw in watchlist.get("keywords", [])]
        self.companies = watchlist.get("companies", [])
        self.agencies = [a.lower() for a in watchlist.get("agencies", [])]

    def evaluate(self, item: RawItem) -> RelevanceMatch:
        haystack = f"{item.title}\n{item.content}".lower()

        matched_keywords = [kw for kw in self.keywords if kw in haystack]
        matched_companies = [
            company["name"]
            for company in self.companies
            if company["name"].lower() in haystack
            or company["ticker"].lower() in haystack
        ]
        matched_agency = any(
            agency in item.source_name.lower() for agency in self.agencies
        )

        is_relevant = bool(matched_keywords or matched_companies or matched_agency)

        return RelevanceMatch(
            is_relevant=is_relevant,
            matched_keywords=matched_keywords,
            matched_companies=matched_companies,
            matched_agency=matched_agency,
        )

    def filter(self, items: list[RawItem]) -> list[tuple[RawItem, RelevanceMatch]]:
        """Return only the (item, match) pairs judged relevant."""
        results = []
        for item in items:
            match = self.evaluate(item)
            if match.is_relevant:
                results.append((item, match))
        return results
