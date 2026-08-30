"""Normalize raw source payloads into shared Item objects."""

import hashlib
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from src.models import Item

_TAG_RE = re.compile(r"<[^>]+>")


def make_id(url: str) -> str:
    """Stable unique id: md5 hex of the URL."""
    return hashlib.md5((url or "").encode("utf-8")).hexdigest()


def _strip_html(value: str) -> str:
    text = _TAG_RE.sub("", value or "")
    return " ".join(text.split())


def _published_to_iso(raw: dict) -> str:
    parsed = raw.get("published_parsed")
    if parsed:
        try:
            dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass

    published = raw.get("published")
    if isinstance(published, (int, float)):
        try:
            return datetime.fromtimestamp(published, tz=timezone.utc).isoformat()
        except Exception:
            return ""

    if isinstance(published, str) and published:
        try:
            return parsedate_to_datetime(published).astimezone(timezone.utc).isoformat()
        except Exception:
            return ""
    return ""


def normalize(raw: dict, source_type: str, source: str) -> Item:
    """Convert one raw source dict into a normalized Item."""
    url = str(raw.get("url") or "")
    return Item(
        id=make_id(url),
        title=html.unescape(str(raw.get("title") or "")),
        url=url,
        summary=_strip_html(html.unescape(str(raw.get("summary") or ""))),
        source=source or "",
        source_type=source_type or "",
        published_at=_published_to_iso(raw),
        author=str(raw.get("author") or ""),
    )
