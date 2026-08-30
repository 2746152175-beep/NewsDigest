"""R3 entry point: write summarized news into the Obsidian vault (notes + digest + indexes)."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config_loader import load_config, resolve_path
from src.scheduler.log import setup_logging
from src.write.digest import write_digest
from src.write.favorites import build_favorite_index, load_favorites
from src.write.index import write_indexes
from src.write.note import assign_filenames, extract_published, write_note

logger = logging.getLogger(__name__)


def _load_items(path: Path) -> list[dict] | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    return [it for it in data if isinstance(it, dict) and it.get("id")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R3: write Obsidian notes + digest + indexes")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today (Asia/Shanghai)")
    args = parser.parse_args(argv)

    config = load_config()
    setup_logging(config)

    timezone_name = (config.get("project") or {}).get("timezone") or "Asia/Shanghai"
    tz = ZoneInfo(timezone_name)
    date_str = args.date or datetime.now(tz).date().isoformat()

    data_cfg = config.get("data") or {}
    summarized_dir = resolve_path(data_cfg.get("summarized_dir") or "data/summarized")
    summarized_path = summarized_dir / f"{date_str}.json"
    if not summarized_path.exists():
        logger.error("summarized file not found: %s", summarized_path)
        print(f"[R3] error: summarized file not found: {summarized_path}")
        return 1

    items = _load_items(summarized_path)
    if items is None:
        logger.error("summarized file missing or invalid: %s", summarized_path)
        print(f"[R3] error: summarized file missing or invalid: {summarized_path}")
        return 1
    if not items:
        logger.info("no relevant items to archive for %s", date_str)
        print("[R3] no relevant items, nothing to write")
        return 0

    vault = config.get("vault") or {}
    news_dir = Path(str(vault.get("news_dir") or ""))
    if not news_dir.is_absolute():
        logger.error("vault.news_dir must be absolute: %s", news_dir)
        print(f"[R3] error: vault.news_dir is not absolute: {news_dir}")
        return 1

    company_root = news_dir / (str(vault.get("company_dir") or "01-公司"))
    digest_dir = news_dir / (str(vault.get("digest_dir") or "02-每日简报"))
    index_dir = news_dir / (str(vault.get("index_dir") or "00-索引"))
    archive_dir = news_dir / (str(vault.get("archive_dir") or "03-原文存档"))

    for directory in (company_root, digest_dir, index_dir, archive_dir):
        directory.mkdir(parents=True, exist_ok=True)

    published_by_id = {
        str(item.get("id") or ""): extract_published(item.get("published_at"), date_str)
        for item in items
    }
    filenames = assign_filenames(items, published_by_id)

    favorites = load_favorites(config)

    written = 0
    for item in items:
        item_id = str(item.get("id") or "")
        filename = filenames.get(item_id)
        if not filename:
            logger.warning("no filename assigned for item %s, skipped", item_id)
            continue
        starred = item_id in favorites
        path = write_note(item, published_by_id[item_id], filename, company_root, starred)
        written += 1
        logger.debug("wrote note %s", path)

    digest_path = write_digest(digest_dir, items, filenames, date_str)
    index_paths = write_indexes(index_dir, company_root)

    # 刷新收藏索引
    (index_dir / "收藏.md").write_text(build_favorite_index(company_root), encoding="utf-8")

    logger.info(
        "R3 finished: notes=%d digest=%s indexes=%d",
        written,
        digest_path,
        len(index_paths),
    )
    print(f"[R3] notes written: {written}")
    print(f"[R3] digest: {digest_path}")
    print(f"[R3] indexes: {len(index_paths)} files under {index_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
