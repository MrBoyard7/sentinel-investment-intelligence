"""
Collectors package.

Exposes `build_collector`, a tiny factory that maps a source's declared
`type` (from config/sources.yaml) to the right collector class. Adding a
new collection method (e.g. a future SEC EDGAR API collector) means adding
one class and one line here - nothing else in the pipeline changes.
"""

from __future__ import annotations

from typing import Any

from sentinel.collectors.base import BaseCollector, RawItem
from sentinel.collectors.rss_collector import RSSCollector
from sentinel.collectors.web_scraper import WebScraperCollector

_COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "rss": RSSCollector,
    "scrape": WebScraperCollector,
}


def build_collector(source_config: dict[str, Any]) -> BaseCollector:
    source_type = source_config.get("type")
    collector_cls = _COLLECTOR_REGISTRY.get(source_type)
    if collector_cls is None:
        raise ValueError(
            f"Unknown source type '{source_type}' for source "
            f"'{source_config.get('id')}'. Known types: "
            f"{list(_COLLECTOR_REGISTRY)}"
        )
    return collector_cls(source_config)


__all__ = ["BaseCollector", "RawItem", "build_collector"]
