"""
SQLAlchemy model for the `items` table.

One row = one intelligence item that made it past the relevance filter and
was scored by the AI (or the heuristic fallback). This is the single
source of truth that both the dashboard and the alert engine read from.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source_id: Mapped[str] = mapped_column(String(100), index=True)
    source_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), index=True)

    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    published_at: Mapped[str] = mapped_column(String(50))

    score: Mapped[int] = mapped_column(Integer, index=True)
    sentiment: Mapped[str] = mapped_column(String(20), index=True)
    summary: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    scoring_method: Mapped[str] = mapped_column(String(30))

    notes: Mapped[str] = mapped_column(Text, default="")

    collected_at: Mapped[str] = mapped_column(
        String(50), default=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Alerting bookkeeping - lets the alert engine avoid re-notifying on an
    # item it has already surfaced in an immediate alert or a digest.
    immediate_alert_sent: Mapped[bool] = mapped_column(default=False)
    included_in_daily_digest: Mapped[bool] = mapped_column(default=False)
    included_in_weekly_digest: Mapped[bool] = mapped_column(default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "category": self.category,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "score": self.score,
            "sentiment": self.sentiment,
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "recommended_action": self.recommended_action,
            "scoring_method": self.scoring_method,
            "notes": self.notes,
            "collected_at": self.collected_at,
        }
