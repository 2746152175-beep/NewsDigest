"""R3 note builder: turn one summarized item into an Obsidian markdown note."""

from __future__ import annotations

import re
from pathlib import Path

_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')
_WHITESPACE = re.compile(r"\s+")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

MAX_TITLE_LEN = 30


def clean_title(title: str) -> str:
    """Sanitize a title into a safe, compact filename component."""
    text = str(title or "")
    text = _ILLEGAL_CHARS.sub("-", text)
    text = _WHITESPACE.sub(" ", text).strip()
    if len(text) > MAX_TITLE_LEN:
        text = text[:MAX_TITLE_LEN]
    return text.rstrip(" -。，！？：；、,.!?:;")


def extract_published(published_at: str | None, fallback: str) -> str:
    """Return YYYY-MM-DD from an ISO timestamp, falling back to the run date."""
    match = _DATE_RE.search(str(published_at or ""))
    return match.group(1) if match else fallback


def _yaml_str(value: object) -> str:
    text = "" if value is None else str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _yaml_list(values: object) -> str:
    vals = [v for v in (values or []) if str(v).strip()]
    if not vals:
        return "[]"
    return "[" + ", ".join(_yaml_str(v) for v in vals) + "]"


def _companies(item: dict) -> list[str]:
    return [str(c).strip() for c in (item.get("company") or []) if str(c).strip()]


def _segments(item: dict) -> list[str]:
    return [str(s).strip() for s in (item.get("segment") or []) if str(s).strip()]


def build_tags(item: dict) -> list[str]:
    """Flatten category + segments + companies, replacing spaces with dashes."""
    parts: list[str] = []
    category = str(item.get("category") or "").strip()
    if category:
        parts.append(category)
    parts.extend(_segments(item))
    parts.extend(_companies(item))

    tags: list[str] = []
    seen: set[str] = set()
    for part in parts:
        tag = part.replace(" ", "-")
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def _importance(item: dict) -> int:
    try:
        return int(item.get("importance"))
    except (TypeError, ValueError):
        return 0


def build_frontmatter(item: dict, published: str) -> str:
    fields = [
        "type: news",
        f"id: {_yaml_str(item.get('id'))}",
        f"title: {_yaml_str(item.get('title'))}",
        f"company: {_yaml_list(_companies(item))}",
        f"category: {_yaml_str(item.get('category'))}",
        f"segment: {_yaml_list(_segments(item))}",
        f"source: {_yaml_str(item.get('source'))}",
        f"url: {_yaml_str(item.get('url'))}",
        f"published: {_yaml_str(published)}",
        f"importance: {_importance(item)}",
        f"tags: {_yaml_list(build_tags(item))}",
    ]
    return "---\n" + "\n".join(fields) + "\n---"


def build_body(item: dict) -> str:
    summary = str(item.get("summary") or "").strip()
    insight = str(item.get("insight") or "").strip()
    points = [str(p).strip() for p in (item.get("key_points") or []) if str(p).strip()]
    url = str(item.get("url") or "").strip()

    parts = ["## 内容概括", "", summary, "", "## 内容总结 / 产业启示", "", insight]
    if points:
        parts += ["", "## 要点", ""]
        parts += [f"- {p}" for p in points]
    parts += ["", "## 原文", "", f"[查看原文](<{url}>)"]
    return "\n".join(parts).rstrip() + "\n"


def build_note(item: dict, published: str) -> str:
    return build_frontmatter(item, published) + "\n\n" + build_body(item)


def base_filename(item: dict, published: str) -> str:
    text = item.get("summary") or item.get("title")
    return f"{published} {clean_title(text)}"


def assign_filenames(items: list[dict], published_by_id: dict[str, str]) -> dict[str, str]:
    """Assign deterministic note filenames, resolving title collisions with id prefixes."""
    groups: dict[str, list[str]] = {}
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        base = base_filename(item, published_by_id.get(item_id, ""))
        groups.setdefault(base, []).append(item_id)

    filenames: dict[str, str] = {}
    for base, ids in groups.items():
        for index, item_id in enumerate(sorted(ids)):
            filenames[item_id] = base if index == 0 else f"{base}-{item_id[:6]}"
    return filenames


def company_dir_for(item: dict, company_root: Path) -> Path:
    companies = _companies(item)
    name = companies[0] if companies else "_行业动态"
    safe_name = _ILLEGAL_CHARS.sub("-", name).strip() or "_行业动态"
    return company_root / safe_name


def write_note(item: dict, published: str, filename: str, company_root: Path) -> Path:
    target_dir = company_dir_for(item, company_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{filename}.md"
    path.write_text(build_note(item, published), encoding="utf-8")
    return path
