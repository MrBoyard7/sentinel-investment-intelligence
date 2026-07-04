"""
Prompt templates used by sentinel.ai.scorer.

Kept in a dedicated module (rather than inlined in the scorer) so that
prompt iteration - the part of this kind of system that changes most
often in practice - never requires touching any control-flow code.
"""

from __future__ import annotations

from typing import Any

from sentinel.collectors.base import RawItem
from sentinel.relevance import RelevanceMatch

SYSTEM_PROMPT = """\
You are an investment intelligence analyst. You review government, \
regulatory, legal, and industry developments and assess their importance \
to a specific investment theme and its associated publicly traded \
companies.

You always respond with a single, valid JSON object and nothing else - no \
markdown code fences, no preamble, no explanation outside the JSON.

The JSON object must have exactly these keys:
  "score": integer from 1 to 5 (1 = noise, 5 = market-moving / urgent)
  "sentiment": one of "Positive", "Negative", "Neutral"
  "category": short string, e.g. "Permitting", "Policy", "Litigation",
              "Funding", "Corporate", "Enforcement"
  "summary": 1-2 sentence plain-English summary of what happened
  "why_it_matters": 1-2 sentences on the investment implication
  "recommended_action": short actionable phrase, e.g. "Monitor for follow-up
              rulemaking", "Flag for portfolio review", "No action needed"

Be conservative with high scores (4-5): reserve them for developments that \
could plausibly move a stock price, change permitting timelines, or shift \
policy in a way that affects the theme. Routine, procedural, or purely \
informational items should score 1-2.\
"""


def build_user_prompt(
    item: RawItem, match: RelevanceMatch, theme: dict[str, Any]
) -> str:
    matched_bits = []
    if match.matched_keywords:
        matched_bits.append(f"Matched keywords: {', '.join(match.matched_keywords)}")
    if match.matched_companies:
        matched_bits.append(f"Matched companies: {', '.join(match.matched_companies)}")
    if match.matched_agency:
        matched_bits.append("Source is a watchlisted government agency.")
    matched_summary = (
        "\n".join(matched_bits) if matched_bits else "No direct keyword match."
    )

    return f"""\
Investment theme: {theme.get('name', 'Unspecified')}
Theme description: {theme.get('description', '')}

Source: {item.source_name} ({item.category})
Published: {item.published_at}
Title: {item.title}
URL: {item.url}

Content:
{item.content[:3000]}

Relevance signal from the pre-filter:
{matched_summary}

Analyze this item and return the JSON object described in your instructions.\
"""
