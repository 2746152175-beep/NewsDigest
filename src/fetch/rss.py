"""RSS feed fetcher built on feedparser."""

import logging
import re

import feedparser

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_summary(value: str) -> str:
    text = _TAG_RE.sub("", value or "")
    return " ".join(text.split())


def _extract_entry(entry: dict, source_name: str) -> dict:
    return {
        "title": entry.get("title") or "",
        "url": entry.get("link") or "",
        "summary": _clean_summary(entry.get("summary") or ""),
        "author": entry.get("author") or "",
        "published": entry.get("published") or "",
        "published_parsed": entry.get("published_parsed"),
        "source": source_name,
        "source_type": "rss",
    }


def fetch_rss(feeds: list[dict]) -> list[dict]:
    """Fetch every RSS feed; a single failing feed must not stop the rest."""
    items: list[dict] = []
    for feed in feeds:
        name = feed.get("name") or "unknown"
        url = feed.get("url")
        if not url:
            logger.warning("RSS feed %s has no url, skipped", name)
            continue
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                raise ValueError(parsed.get("bozo_exception") or "parse failed")
            for entry in parsed.entries:
                items.append(_extract_entry(entry, name))
            logger.info("RSS %s: %d entries", name, len(parsed.entries))
        except Exception as exc:
            logger.error("RSS feed %s failed: %s", name, exc)
    return items
