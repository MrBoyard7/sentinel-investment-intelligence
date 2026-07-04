"""
Database access layer.

A thin wrapper around SQLAlchemy that exposes exactly the operations the
rest of the system needs: initializing the schema, inserting a scored
item (with de-duplication by URL), and a handful of read queries used by
the dashboard API and the alert engine.

SQLite is intentionally used here (see docs/architecture.md for the
rationale): it requires zero setup for a portfolio/demo deployment while
the SQLAlchemy layer keeps a swap to Postgres a one-line change for a
production deployment with concurrent writers.
"""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sentinel.ai.scorer import ScoredItem
from sentinel.settings import settings
from sentinel.storage.models import Base, Item

_engine = create_engine(f"sqlite:///{settings.database_full_path}", echo=False)


def init_db() -> None:
    """Create the schema if it does not already exist. Safe to call repeatedly."""
    Base.metadata.create_all(_engine)


def insert_scored_items(scored_items: Iterable[ScoredItem]) -> list[Item]:
    """
    Insert scored items, skipping any URL already present in the database.

    Returns the list of newly-inserted Item rows (as detached dicts would
    lose their id, callers that need alerting information should read the
    fields off these ORM objects before the session closes, or call
    `.to_dict()` immediately).
    """
    inserted: list[Item] = []
    with Session(_engine) as session:
        for scored in scored_items:
            existing = session.execute(
                select(Item.id).where(Item.url == scored.url)
            ).scalar_one_or_none()
            if existing is not None:
                continue

            row = Item(
                source_id=scored.source_id,
                source_name=scored.source_name,
                category=scored.category,
                title=scored.title,
                url=scored.url,
                published_at=scored.published_at,
                score=scored.score,
                sentiment=scored.sentiment,
                summary=scored.summary,
                why_it_matters=scored.why_it_matters,
                recommended_action=scored.recommended_action,
                scoring_method=scored.scoring_method,
            )
            session.add(row)
            inserted.append(row)

        session.commit()
        for row in inserted:
            session.refresh(row)
        # Detach so callers can use these objects after the session closes.
        for row in inserted:
            session.expunge(row)
    return inserted


def get_items(
    min_score: int | None = None,
    category: str | None = None,
    sentiment: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Query items for the dashboard API, most recent first."""
    with Session(_engine) as session:
        stmt = select(Item).order_by(Item.collected_at.desc()).limit(limit)
        if min_score is not None:
            stmt = stmt.where(Item.score >= min_score)
        if category:
            stmt = stmt.where(Item.category == category)
        if sentiment:
            stmt = stmt.where(Item.sentiment == sentiment)

        rows = session.execute(stmt).scalars().all()
        return [row.to_dict() for row in rows]


def get_pending_immediate_alerts(min_score: int) -> list[Item]:
    with Session(_engine) as session:
        stmt = select(Item).where(
            Item.score >= min_score, Item.immediate_alert_sent.is_(False)
        )
        rows = session.execute(stmt).scalars().all()
        session.expunge_all()
        return rows


def mark_immediate_alert_sent(item_ids: list[int]) -> None:
    _mark_flag(item_ids, "immediate_alert_sent")


def get_items_for_digest(digest_type: str) -> list[Item]:
    flag = (
        "included_in_daily_digest"
        if digest_type == "daily"
        else "included_in_weekly_digest"
    )
    with Session(_engine) as session:
        stmt = select(Item).where(getattr(Item, flag).is_(False))
        rows = session.execute(stmt).scalars().all()
        session.expunge_all()
        return rows


def mark_included_in_digest(item_ids: list[int], digest_type: str) -> None:
    flag = (
        "included_in_daily_digest"
        if digest_type == "daily"
        else "included_in_weekly_digest"
    )
    _mark_flag(item_ids, flag)


def _mark_flag(item_ids: list[int], flag: str) -> None:
    if not item_ids:
        return
    with Session(_engine) as session:
        rows = (
            session.execute(select(Item).where(Item.id.in_(item_ids))).scalars().all()
        )
        for row in rows:
            setattr(row, flag, True)
        session.commit()


def get_stats() -> dict:
    """Aggregate counts used by the dashboard's summary strip and chart."""
    with Session(_engine) as session:
        all_items = session.execute(select(Item)).scalars().all()

    total = len(all_items)
    high_priority = sum(
        1 for i in all_items if i.score >= settings.immediate_alert_score
    )
    by_category: dict[str, int] = {}
    by_sentiment: dict[str, int] = {"Positive": 0, "Negative": 0, "Neutral": 0}

    for i in all_items:
        by_category[i.category] = by_category.get(i.category, 0) + 1
        by_sentiment[i.sentiment] = by_sentiment.get(i.sentiment, 0) + 1

    return {
        "total_items": total,
        "high_priority_items": high_priority,
        "by_category": by_category,
        "by_sentiment": by_sentiment,
    }
