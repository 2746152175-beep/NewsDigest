"""R3 daily digest: group one day's notes by category into a single markdown file."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


def _summary_head(item: dict) -> str:
    return str(item.get("summary") or "").strip()[:30]


def build_digest(items: list[dict], filenames: dict[str, str], date_str: str) -> str:
    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        category = str(item.get("category") or "").strip() or "未分类"
        by_category[category].append(item)

    lines = [f"# 每日简报 {date_str}", "", f"> 共 {len(items)} 条相关新闻"]
    for category in sorted(by_category):
        lines.append("")
        lines.append(f"## {category}")
        group = sorted(
            by_category[category],
            key=lambda it: filenames.get(str(it.get("id") or ""), ""),
        )
        for item in group:
            name = filenames.get(str(item.get("id") or ""), "")
            if name:
                lines.append(f"- [[{name}]] — {_summary_head(item)}")
    return "\n".join(lines).rstrip() + "\n"


def write_digest(
    digest_dir: Path,
    items: list[dict],
    filenames: dict[str, str],
    date_str: str,
) -> Path:
    digest_dir.mkdir(parents=True, exist_ok=True)
    path = digest_dir / f"{date_str}.md"
    path.write_text(build_digest(items, filenames, date_str), encoding="utf-8")
    return path
