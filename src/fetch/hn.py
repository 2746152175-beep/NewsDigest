"""Hacker News fetcher built on httpx."""

import logging

import httpx

logger = logging.getLogger(__name__)

_DISCUSSION_URL = "https://news.ycombinator.com/item?id={id}"


def _get_json(client: httpx.Client, url: str):
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def fetch_hn(cfg: dict) -> list[dict]:
    """Fetch Hacker News top stories from the configured API endpoints."""
    if not cfg.get("enabled", True):
        logger.info("Hacker News disabled in config, skipped")
        return []

    top_url = cfg.get("topstories_url")
    item_url = cfg.get("item_url")
    max_items = int(cfg.get("max_items") or 50)
    if not top_url or not item_url:
        logger.error("Hacker News config missing topstories_url or item_url")
        return []

    timeout = float(cfg.get("timeout") or 15.0)
    items: list[dict] = []
    with httpx.Client(timeout=timeout) as client:
        try:
            story_ids = _get_json(client, top_url)
        except Exception as exc:
            logger.error("Hacker News topstories failed: %s", exc)
            return []

        if not isinstance(story_ids, list):
            logger.error("Hacker News topstories returned unexpected payload")
            return []

        for story_id in story_ids[:max_items]:
            try:
                data = _get_json(client, item_url.format(id=story_id))
            except Exception as exc:
                logger.warning("Hacker News item %s failed: %s", story_id, exc)
                continue
            if not isinstance(data, dict):
                continue
            if data.get("type") != "story":
                continue
            if data.get("deleted") or data.get("dead"):
                continue
            story_url = data.get("url") or _DISCUSSION_URL.format(id=story_id)
            items.append(
                {
                    "title": data.get("title") or "",
                    "url": story_url,
                    "summary": data.get("text") or "",
                    "author": data.get("by") or "",
                    "published": data.get("time"),
                    "source": "Hacker News",
                    "source_type": "hacker_news",
                }
            )

    logger.info("Hacker News: %d stories fetched", len(items))
    return items
