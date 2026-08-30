"""收藏（favorite）管理：favorites.json 读写、Obsidian 笔记标记、收藏索引。"""

import json
from pathlib import Path

import yaml

from src.config_loader import resolve_path

STAR_TAG = "收藏"


def favorites_path(config: dict) -> Path:
    summarized = resolve_path((config.get("data") or {}).get("summarized_dir") or "新闻数据/summarized")
    return summarized.parent / "favorites.json"


def load_favorites(config: dict) -> set[str]:
    path = favorites_path(config)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {str(x) for x in data} if isinstance(data, list) else set()


def save_favorites(config: dict, ids: set[str]) -> None:
    path = favorites_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")


def set_favorite(config: dict, item_id: str, starred: bool) -> None:
    ids = load_favorites(config)
    if starred:
        ids.add(item_id)
    else:
        ids.discard(item_id)
    save_favorites(config, ids)


def _split_frontmatter(text: str) -> tuple[str, str]:
    text = text.lstrip("﻿")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1 :])
    return "", text


def find_note_by_id(company_dir: Path, item_id: str) -> Path | None:
    if not company_dir.exists():
        return None
    for path in company_dir.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        fm, _ = _split_frontmatter(text)
        if not fm:
            continue
        try:
            data = yaml.safe_load(fm)
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and str(data.get("id") or "") == item_id:
            return path
    return None


def set_note_starred(note_path: Path, starred: bool) -> None:
    text = note_path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    if not fm:
        return
    try:
        data = yaml.safe_load(fm)
    except yaml.YAMLError:
        return
    if not isinstance(data, dict):
        data = {}
    if starred:
        data["starred"] = True
    else:
        data.pop("starred", None)
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags = [str(t) for t in tags if str(t).strip()]
    if starred and STAR_TAG not in tags:
        tags.append(STAR_TAG)
    elif not starred:
        tags = [t for t in tags if t != STAR_TAG]
    data["tags"] = tags
    new_fm = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    note_path.write_text(f"---\n{new_fm}---\n{body}", encoding="utf-8")


def build_favorite_index(company_dir: Path) -> str:
    lines = ["# 收藏", "", "> 收藏的重点新闻（带 #收藏 标签，关系图谱中可按 tag:#收藏 染色）", ""]
    names: list[str] = []
    if company_dir.exists():
        for path in company_dir.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            fm, _ = _split_frontmatter(text)
            if not fm:
                continue
            try:
                data = yaml.safe_load(fm)
            except yaml.YAMLError:
                continue
            if isinstance(data, dict) and data.get("starred") is True:
                names.append(path.stem)
    for name in sorted(names):
        lines.append(f"- [[{name}]]")
    return "\n".join(lines).rstrip() + "\n"
