"""Fetch and extract readable article body text using trafilatura."""

from __future__ import annotations

import trafilatura

DEFAULT_MAX_CHARS = 3000


def fetch_body(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Download ``url`` and return extracted plain-text body.

    Returns an empty string when the URL is empty, the download fails, or no
    readable text is extracted. The caller is expected to fall back to the
    item's RSS summary on an empty result.
    """
    if not url:
        return ""

    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(
            downloaded,
            url=url,
            include_comments=False,
            include_tables=False,
            include_formatting=False,
        )
    except Exception:
        return ""

    text = (text or "").strip()
    if not text:
        return ""
    if len(text) > max_chars:
        text = text[:max_chars]
    return text
