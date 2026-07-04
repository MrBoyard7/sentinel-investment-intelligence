"""
Collector for sources that do not publish a usable RSS feed, such as the
White House "Presidential Actions" page or a company's investor-relations
press release listing.

Selectors are declared per-source in config/sources.yaml so that adding a
new scraped source never requires touching this file:

    list_selector:  CSS selector matching each repeating item container
    title_selector: CSS selector (relative to the item) for the title/link element
    link_selector:  CSS selector (relative to the item) for the link element
    date_selector:  CSS selector (relative to the item) for a date/time element

This keeps the scraper generic across very differently-styled government
and investor-relations pages, at the cost of needing a small selector
update if a target site redesigns its markup - an inherent trade-off of
scraping vs. consuming a structured feed.
"""

from __future__ import annotations

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from sentinel.collectors.base import BaseCollector, RawItem

REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "Sentinel-Intelligence-Bot/1.0 (+https://github.com/)"


class WebScraperCollector(BaseCollector):
    """Collects items from a source configured with `type: scrape`."""

    def _collect_live(self) -> list[RawItem]:
        url = self.source_config["url"]
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        list_selector = self.source_config["list_selector"]
        title_selector = self.source_config["title_selector"]
        link_selector = self.source_config.get("link_selector", title_selector)
        date_selector = self.source_config.get("date_selector")

        items: list[RawItem] = []
        for node in soup.select(list_selector):
            title_el = node.select_one(title_selector)
            link_el = node.select_one(link_selector)
            if title_el is None or link_el is None:
                continue

            title = title_el.get_text(strip=True)
            href = link_el.get("href", "")
            link = self._absolutize(href, url)

            published_at = datetime.now(timezone.utc).isoformat()
            if date_selector:
                date_el = node.select_one(date_selector)
                if date_el is not None:
                    published_at = date_el.get("datetime") or date_el.get_text(
                        strip=True
                    )

            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    category=self.category,
                    title=title,
                    url=link,
                    published_at=published_at,
                    content=node.get_text(" ", strip=True),
                )
            )
        return items

    @staticmethod
    def _absolutize(href: str, base_url: str) -> str:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        from urllib.parse import urljoin

        return urljoin(base_url, href)
