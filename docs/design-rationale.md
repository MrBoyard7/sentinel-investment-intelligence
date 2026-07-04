# Design rationale

This document captures the reasoning behind decisions that a code review
alone won't make obvious — in particular, how the system avoids false
positives and alert fatigue, how it extends to a new investment theme, and
rough cost/timeline planning for a real deployment.

## Preventing false positives and alert fatigue

Three independent layers work together, so no single mistake floods the
inbox:

1. **Relevance pre-filter (`sentinel/relevance.py`).** A cheap,
   deterministic keyword/company/agency match runs before anything reaches
   the AI. This is the first and cheapest filter: an item about, say, a
   city council meeting never reaches the scorer at all, regardless of what
   the AI might have said about it.

2. **AI importance scoring, not AI relevance scoring.** The AI is
   deliberately never asked "is this relevant?" — the pre-filter already
   answered that. It is asked "how important is this, on a scale where 1-2
   is routine and 4-5 is rare," with an explicit instruction to be
   conservative with high scores. Separating "is this in scope" from "how
   much does this matter" keeps the AI's judgment calibrated on a narrower,
   more reliable question.

3. **Score-gated routing, not source-gated routing.** Every item is stored
   and visible on the dashboard, but only score >= `IMMEDIATE_ALERT_SCORE`
   (default 4) triggers an immediate email/Slack/SMS. Everything else waits
   for the daily or weekly digest. This means a noisy source can't spam
   immediate alerts — it can, at worst, add rows to a digest email the
   recipient reads once a day.

De-duplication (`database.insert_scored_items`, keyed on URL) also prevents
the same announcement from re-triggering an alert if a source republishes
or re-syndicates it.

In production, the two knobs most worth tuning after the first few weeks of
real data are `IMMEDIATE_ALERT_SCORE` and the keyword list itself — both are
plain configuration, not code, so they can be adjusted without a deploy.

## Extending to a new investment theme

Everything theme-specific lives in `config/watchlist.yaml` and
`config/sources.yaml`. Standing up a second dashboard for, say, "domestic
semiconductor manufacturing incentives" is:

1. Duplicate both YAML files with new keywords, companies, and sources.
2. Point a second instance of the pipeline/dashboard at them (e.g. via a
   `CONFIG_PROFILE` environment variable, or a separate deployment).
3. No changes to `sentinel/collectors`, `sentinel/ai`, `sentinel/storage`,
   `sentinel/dashboard`, or `sentinel/alerts` are required.

This is the concrete mechanism behind the brief's note that "this project
may expand into multiple monitoring dashboards" — the architecture already
supports that without modification.

## Cost and timeline estimates

These are the kind of estimates the brief's "To Apply" section asks for,
included here for completeness since this repository is meant to double as
a demonstration of how that conversation would be approached:

| Item | Estimate | Notes |
|---|---|---|
| Initial build (Phase 1 scope as specified) | 2-3 weeks | Assumes the sources listed in the brief; scraped sources (vs. RSS) add roughly half a day each for selector maintenance and testing |
| Monthly maintenance | 3-6 hours/month | Mostly selector upkeep for scraped sources if a target site redesigns, plus periodic keyword/threshold tuning based on false-positive feedback |
| Monthly running cost (AI + infrastructure) | Low, usage-based | Dominated by OpenAI API calls; cost scales with (a) number of sources, (b) polling frequency, and (c) how aggressively the relevance pre-filter narrows volume before it reaches the AI — the pre-filter is the main lever for controlling this |

Actual numbers depend heavily on final source count and polling frequency,
which is why the pre-filter and the score-gated alert design above matter:
they are what keep both AI spend and alert volume proportional to genuinely
important developments rather than total source volume.

## Testing approach

`tests/` covers the three places where a silent regression would be most
costly:

- `test_relevance.py` — the pre-filter correctly includes/excludes items on
  keyword, company, ticker, and agency matches.
- `test_scorer.py` — the heuristic fallback scorer stays within bounds and
  responds sensibly to positive/negative language, so demo mode (and the
  production fallback path) never emits an invalid or absurd score.
- `test_pipeline.py` — a full end-to-end pass against the demo fixtures,
  including a de-duplication check, run against an isolated in-memory
  database so tests never touch real data.

Run them with:

```bash
pip install -r requirements-dev.txt
pytest
```
