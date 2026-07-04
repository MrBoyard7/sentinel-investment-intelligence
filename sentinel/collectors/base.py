"""
Shared data model and base class for all collectors.

A collector's only job is to turn "a source" into a list of RawItem
objects. It knows nothing about relevance filtering, AI scoring, storage,
or alerting - that separation is what lets us add a new source (a new
RSS feed, a new agency scraper, a future SEC-EDGAR or PACER integration)
without touching any other part of the pipeline.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sentinel.settings import DEMO_FIXTURES_DIR, settings


@dataclass
class RawItem:
    """A single piece of content collected from a source, before scoring."""

    source_id: str
    source_name: str
    category: str
    title: str
    url: str
    published_at: str  # ISO-8601 string, kept as a string until it hits storage
    content: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseCollector(ABC):
    """
    Common interface for every collector.

    Subclasses implement `_collect_live()` for the real, network-backed
    behavior. `collect()` is the public entry point used by the pipeline;
    it transparently swaps in fixture data when DEMO_MODE is enabled, so
    the exact same pipeline code path runs whether or not real credentials
    and network access are available.
    """

    def __init__(self, source_config: dict[str, Any]):
        self.source_config = source_config
        self.source_id: str = source_config["id"]
        self.source_name: str = source_config["name"]
        self.category: str = source_config.get("category", "Uncategorized")

    def collect(self) -> list[RawItem]:
        if settings.demo_mode:
            return self._collect_demo()
        try:
            return self._collect_live()
        except (
            Exception
        ) as exc:  # noqa: BLE001 - collectors must never crash the pipeline
            print(
                f"[{self.source_id}] live collection failed ({exc}); "
                f"falling back to demo fixtures for this run."
            )
            return self._collect_demo()

    @abstractmethod
    def _collect_live(self) -> list[RawItem]:
        """Fetch real data from the network. Implemented by subclasses."""

    def _collect_demo(self) -> list[RawItem]:
        """
        Load a fixture file matching this source's id, if one exists.

        Fixtures live at data/demo_fixtures/<source_id>.json and contain a
        list of objects shaped like RawItem's fields. This lets the whole
        pipeline (collection -> relevance filter -> AI scoring -> storage
        -> dashboard -> alerts) run end-to-end with zero network access
        and zero API keys, which is what makes this repository reviewable
        by simply cloning it and running `python -m sentinel.cli seed-demo`.
        """
        fixture_path = Path(DEMO_FIXTURES_DIR) / f"{self.source_id}.json"
        if not fixture_path.exists():
            return []

        with fixture_path.open("r", encoding="utf-8") as handle:
            raw_entries = json.load(handle)

        items = []
        for entry in raw_entries:
            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    category=self.category,
                    title=entry["title"],
                    url=entry["url"],
                    published_at=entry.get(
                        "published_at", datetime.now(timezone.utc).isoformat()
                    ),
                    content=entry.get("content", ""),
                )
            )
        return items
