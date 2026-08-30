"""R3 index MOC: scan note frontmatter and rebuild company/category/segment indexes."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml


def parse_frontmatter(text: str) -> dict | None:
    """Parse a leading YAML frontmatter block with a simple split plus safe_load."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return None

    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def scan_notes(company_dir: Path) -> list[dict]:
    notes: list[dict] = []
    if not company_dir.exists():
        return notes
    for path in sorted(company_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        frontmatter = parse_frontmatter(text)
        if not frontmatter or frontmatter.get("type") != "news":
            continue
        notes.append({"filename": path.stem, "frontmatter": frontmatter})
    return notes


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        values = [value]
    else:
        values = value or []
    return [str(v).strip() for v in values if str(v).strip()]


def _category(frontmatter: dict) -> str:
    return str(frontmatter.get("category") or "").strip() or "未分类"


def _company_groups(notes: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        companies = _string_list(note["frontmatter"].get("company"))
        if companies:
            for company in companies:
                groups[company].append(note["filename"])
        else:
            groups["_行业动态"].append(note["filename"])
    return groups


def _category_groups(notes: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        groups[_category(note["frontmatter"])].append(note["filename"])
    return groups


def _segment_groups(notes: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        segments = _string_list(note["frontmatter"].get("segment"))
        if segments:
            for segment in segments:
                groups[segment].append(note["filename"])
        else:
            groups["未分类"].append(note["filename"])
    return groups


def _render(title: str, groups: dict[str, list[str]]) -> str:
    lines = [f"# {title}"]
    for group_name in sorted(groups):
        lines.append("")
        lines.append(f"## {group_name}")
        for filename in sorted(groups[group_name]):
            lines.append(f"- [[{filename}]]")
    return "\n".join(lines).rstrip() + "\n"


def build_company_index(notes: list[dict]) -> str:
    return _render("公司索引", _company_groups(notes))


def build_category_index(notes: list[dict]) -> str:
    return _render("分类索引", _category_groups(notes))


def build_segment_index(notes: list[dict]) -> str:
    return _render("领域索引", _segment_groups(notes))


def write_indexes(index_dir: Path, company_dir: Path) -> list[Path]:
    index_dir.mkdir(parents=True, exist_ok=True)
    notes = scan_notes(company_dir)
    files = {
        "公司索引.md": build_company_index(notes),
        "分类索引.md": build_category_index(notes),
        "领域索引.md": build_segment_index(notes),
    }
    written: list[Path] = []
    for name, content in files.items():
        path = index_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
