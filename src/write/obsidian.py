"""从 Obsidian 笔记读取新闻（作为 summarized 文件的兜底数据源）。"""

import re
from pathlib import Path

import yaml


def _company_root(config: dict) -> Path:
    news_dir = Path(str((config.get("vault") or {}).get("news_dir") or ""))
    company_dir = str((config.get("vault") or {}).get("company_dir") or "01-公司")
    return news_dir / company_dir


def _split_frontmatter(text: str) -> tuple[dict | None, str]:
    text = text.lstrip("﻿")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_text = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            try:
                fm = yaml.safe_load(fm_text)
            except yaml.YAMLError:
                return None, body
            return (fm if isinstance(fm, dict) else None), body
    return None, text


def _section(body: str, header: str) -> str:
    m = re.search(rf"## {re.escape(header)}[ \t]*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    return m.group(1).strip() if m else ""


def _key_points(body: str) -> list[str]:
    m = re.search(r"## 要点[ \t]*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if not m:
        return []
    return [l.lstrip("- ").strip() for l in m.group(1).splitlines() if l.strip().startswith("-")]


def _note_to_item(fm: dict, body: str) -> dict:
    return {
        "id": str(fm.get("id") or ""),
        "title": str(fm.get("title") or ""),
        "url": str(fm.get("url") or ""),
        "summary": _section(body, "内容概括"),
        "source": str(fm.get("source") or ""),
        "source_type": "obsidian",
        "published_at": str(fm.get("published") or ""),
        "author": "",
        "relevant": True,
        "company": fm.get("company") or [],
        "category": str(fm.get("category") or ""),
        "segment": fm.get("segment") or [],
        "importance": int(fm.get("importance") or 0),
        "reason": "",
        "insight": _section(body, "内容总结 / 产业启示"),
        "key_points": _key_points(body),
    }


def load_notes_by_date(config: dict, date_str: str) -> list[dict]:
    root = _company_root(config)
    if not root.exists():
        return []
    items: list[dict] = []
    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        fm, body = _split_frontmatter(text)
        if not fm or not fm.get("id"):
            continue
        if str(fm.get("published") or "") != date_str:
            continue
        items.append(_note_to_item(fm, body))
    items.sort(key=lambda it: (-(it.get("importance") or 0), it.get("published_at") or ""))
    return items


def list_note_dates(config: dict) -> set[str]:
    root = _company_root(config)
    if not root.exists():
        return set()
    dates: set[str] = set()
    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        fm, _ = _split_frontmatter(text)
        if not fm:
            continue
        d = str(fm.get("published") or "")
        if d:
            dates.add(d)
    return dates
