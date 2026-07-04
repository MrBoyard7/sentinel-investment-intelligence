"""
Pipeline orchestrator.

This module is the concrete implementation of the required workflow:

    Source -> Collection Method -> AI Analysis -> Dashboard -> Alert

`run_once()` executes exactly one pass over every configured source and
is what both the CLI and the scheduler call. `run_scheduler()` wraps it
in APScheduler so Sentinel can run unattended: a frequent scan pass, plus
a daily and weekly digest.
"""

from __future__ import annotations

from sentinel.ai.scorer import score_item
from sentinel.alerts.digest import send_digest, send_immediate_alert
from sentinel.collectors import build_collector
from sentinel.relevance import RelevanceFilter
from sentinel.settings import load_sources, load_watchlist, settings
from sentinel.storage import database


def run_once() -> dict:
    """
    Run one full pipeline pass:
      1. Collect raw items from every configured source
      2. Filter for relevance against the watchlist
      3. Score relevant items with AI (or the heuristic fallback)
      4. Store new items (de-duplicated by URL)
      5. Send immediate alerts for anything above the score threshold

    Returns a small summary dict, useful for logging and for the CLI's
    printed output.
    """
    database.init_db()

    watchlist = load_watchlist()
    sources = load_sources()
    relevance_filter = RelevanceFilter(watchlist)

    collected_count = 0
    relevant_count = 0
    scored_items = []

    for source_config in sources:
        collector = build_collector(source_config)
        raw_items = collector.collect()
        collected_count += len(raw_items)

        for item, match in relevance_filter.filter(raw_items):
            relevant_count += 1
            scored_items.append(score_item(item, match, watchlist))

    inserted_rows = database.insert_scored_items(scored_items)

    immediate_threshold = watchlist.get(
        "immediate_alert_score", settings.immediate_alert_score
    )
    alerted_ids = []
    for row in inserted_rows:
        if row.score >= immediate_threshold:
            send_immediate_alert(row)
            alerted_ids.append(row.id)
    if alerted_ids:
        database.mark_immediate_alert_sent(alerted_ids)

    return {
        "sources_scanned": len(sources),
        "items_collected": collected_count,
        "items_relevant": relevant_count,
        "items_stored": len(inserted_rows),
        "immediate_alerts_sent": len(alerted_ids),
    }


def run_daily_digest() -> dict:
    database.init_db()
    items = database.get_items_for_digest("daily")
    send_digest(items, "daily")
    database.mark_included_in_digest([i.id for i in items], "daily")
    return {"items_in_digest": len(items)}


def run_weekly_digest() -> dict:
    database.init_db()
    items = database.get_items_for_digest("weekly")
    send_digest(items, "weekly")
    database.mark_included_in_digest([i.id for i in items], "weekly")
    return {"items_in_digest": len(items)}


def run_scheduler(scan_interval_minutes: int = 30) -> None:
    """
    Start a long-running scheduler process:
      - `run_once` every `scan_interval_minutes`
      - daily digest at 08:00
      - weekly digest Monday at 08:15

    This is one reasonable production topology; a Make.com/Zapier
    deployment of the same architecture would replace this function with
    a scheduled scenario/zap calling the same underlying steps.
    """
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler()
    scheduler.add_job(run_once, "interval", minutes=scan_interval_minutes, id="scan")
    scheduler.add_job(run_daily_digest, "cron", hour=8, minute=0, id="daily_digest")
    scheduler.add_job(
        run_weekly_digest,
        "cron",
        day_of_week="mon",
        hour=8,
        minute=15,
        id="weekly_digest",
    )

    print(
        f"Sentinel scheduler started: scanning every {scan_interval_minutes} min, "
        "daily digest at 08:00, weekly digest Monday 08:15. Press Ctrl+C to stop."
    )
    scheduler.start()
