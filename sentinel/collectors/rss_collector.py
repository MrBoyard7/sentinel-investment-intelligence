"""
Collector for standard RSS/Atom feeds (Federal Register, EPA, DOI, DOE, ...).

This is the simplest and most reliable collection method available and
should be preferred over scraping whenever a source publishes a feed.
"""

from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from sentinel.collectors.base import BaseCollector, RawItem


class RSSCollector(BaseCollector):
    """Collects items from a source configured with `type: rss`."""

    def _collect_live(self) -> list[RawItem]:
        url = self.source_config["url"]
        parsed = feedparser.parse(url)

        items: list[RawItem] = []
        for entry in parsed.entries:
            published_at = self._extract_published_at(entry)
            content = self._extract_content(entry)

            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    category=self.category,
                    title=entry.get("title", "(untitled)"),
                    url=entry.get("link", ""),
                    published_at=published_at,
                    content=content,
                )
            )
        return items

    @staticmethod
    def _extract_published_at(entry) -> str:
        for field in ("published_parsed", "updated_parsed"):
            value = getattr(entry, field, None)
            if value:
                dt = datetime(*value[:6], tzinfo=timezone.utc)
                return dt.isoformat()
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _extract_content(entry) -> str:
        if "summary" in entry:
            return entry["summary"]
        if "content" in entry and entry["content"]:
            return entry["content"][0].get("value", "")
        return ""
