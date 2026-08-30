"""R4 orchestrator: run R0 -> R1 -> R2 -> R3 with short-circuit on failure."""

import argparse
import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.classify.classify import main as classify_main
from src.config_loader import load_config, load_sources, resolve_path
from src.fetch.hn import fetch_hn
from src.fetch.normalize import normalize
from src.fetch.rss import fetch_rss
from src.scheduler.dedup import SeenDB
from src.scheduler.log import setup_logging
from src.summarize.summarize import main as summarize_main
from src.write.archive import main as archive_main

logger = logging.getLogger(__name__)


def _load_existing_items(path: Path) -> dict:
    """Load the day file (if any) keyed by item id so re-runs don't wipe it."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, list):
        return {}
    return {item.get("id"): item for item in data if isinstance(item, dict) and item.get("id")}


def _published_sort_key(item: dict) -> str:
    """Sort key: newest published_at first, with missing values last."""
    value = item.get("published_at")
    return value if isinstance(value, str) else ""


def run_fetch(config: dict, date_str: str) -> int:
    """R0: fetch -> normalize -> dedup -> write the daily raw JSON file."""
    sources = load_sources()
    raw_dir = resolve_path((config.get("data") or {}).get("raw_dir") or "data/raw")
    db_path = resolve_path((config.get("dedup") or {}).get("db_path") or "state/seen.db")
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_items: list[dict] = []
    rss_feeds = sources.get("rss_feeds") or []
    if rss_feeds:
        try:
            raw_items.extend(fetch_rss(rss_feeds))
        except Exception as exc:
            logger.error("RSS fetch crashed: %s", exc)

    hn_cfg = sources.get("hacker_news") or {}
    if hn_cfg.get("enabled", True):
        try:
            raw_items.extend(fetch_hn(hn_cfg))
        except Exception as exc:
            logger.error("Hacker News fetch crashed: %s", exc)

    fetched_by_source: dict[str, int] = {}
    for raw in raw_items:
        source = raw.get("source") or "unknown"
        fetched_by_source[source] = fetched_by_source.get(source, 0) + 1

    seen_db = SeenDB(db_path)
    kept_items = []
    skipped = 0
    try:
        for raw in raw_items:
            try:
                item = normalize(
                    raw,
                    raw.get("source_type") or "",
                    raw.get("source") or "",
                )
            except Exception as exc:
                logger.warning("normalize failed for %s: %s", raw.get("url"), exc)
                continue
            if seen_db.is_new(item):
                kept_items.append(item)
            else:
                skipped += 1
        seen_db.commit()
    finally:
        seen_db.close()

    max_items = int((config.get("fetch") or {}).get("max_items", 60) or 60)

    out_path = raw_dir / f"{date_str}.json"
    merged = _load_existing_items(out_path)
    for item in kept_items:
        merged[item.id] = asdict(item)
    payload = list(merged.values())
    payload.sort(key=_published_sort_key, reverse=True)
    if len(payload) > max_items:
        payload = payload[:max_items]
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    source_stats = ", ".join(f"{k}={v}" for k, v in fetched_by_source.items())
    logger.info(
        "R0 finished: fetched=%d new=%d skipped=%d file=%s",
        len(raw_items),
        len(kept_items),
        skipped,
        out_path,
    )
    print(f"[R0] fetched total: {len(raw_items)}")
    print(f"[R0] per-source fetched: {source_stats}")
    print(f"[R0] kept (new): {len(kept_items)}")
    print(f"[R0] skipped (duplicates): {skipped}")
    print(f"[R0] max_items: {max_items}")
    print(f"[R0] selected (after limit): {len(payload)}")
    print(f"[R0] output: {out_path}")
    return 0


def _run_stage(name: str, func, argv: list[str]) -> int:
    """Run one imported stage main() and normalize its result for the summary."""
    print(f"\n===== R{name} start =====")
    try:
        code = int(func(argv))
    except Exception:
        logger.exception("R%s crashed with an unexpected exception", name)
        print(f"[R{name}] ERROR: unhandled exception, see log for details")
        code = 1

    if code == 0:
        logger.info("R%s completed", name)
    else:
        logger.error("R%s failed with exit code %s", name, code)
    return code


def cleanup_data(config: dict) -> None:
    """Delete intermediate data files older than retention_days (default 7)."""
    data_cfg = config.get("data") or {}
    retention = int(data_cfg.get("retention_days", 7) or 7)
    cutoff = (datetime.now() - timedelta(days=retention)).date()
    removed = 0
    for value in (
        data_cfg.get("raw_dir") or "data/raw",
        data_cfg.get("classified_dir") or "data/classified",
        data_cfg.get("summarized_dir") or "data/summarized",
    ):
        directory = resolve_path(value)
        if not directory.exists():
            continue
        for path in directory.glob("*.json"):
            try:
                file_date = datetime.strptime(path.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_date < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
    if removed:
        logger.info("cleaned %d old data files", removed)
        print(f"[cleanup] removed {removed} old data files (older than {retention} days)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R4: run the full news pipeline")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today (Asia/Shanghai)")
    args = parser.parse_args(argv)

    config = load_config()
    setup_logging(config)

    timezone_name = (config.get("project") or {}).get("timezone") or "Asia/Shanghai"
    tz = ZoneInfo(timezone_name)
    date_str = args.date or datetime.now(tz).date().isoformat()
    logger.info("R4 pipeline start for %s", date_str)
    print(f"R4 pipeline date: {date_str}")

    try:
        r0_code = run_fetch(config, date_str)
    except Exception:
        logger.exception("R0 crashed with an unexpected exception")
        print("[R0] ERROR: unhandled exception, see log for details")
        r0_code = 1

    r1_code = None
    r2_code = None
    r3_code = None

    if r0_code != 0:
        logger.error("R0 failed with exit code %s", r0_code)
        print("[R1] skipped: R0 failed")
        print("[R2] skipped: R0 failed")
        print("[R3] skipped: R0 failed")
    else:
        r1_code = _run_stage("1 classify", classify_main, ["--date", date_str])
        if r1_code != 0:
            logger.error("R2 skipped because R1 failed")
            print("[R2] skipped: R1 failed")
            print("[R3] skipped: R1 failed")
        else:
            r2_code = _run_stage("2 summarize", summarize_main, ["--date", date_str])
            if r2_code != 0:
                logger.error("R3 skipped because R2 failed")
                print("[R3] skipped: R2 failed")
            else:
                r3_code = _run_stage("3 archive", archive_main, ["--date", date_str])

    print("\n===== R4 summary =====")
    print(f"R0 fetch: {'success' if r0_code == 0 else 'failed'}")
    print(f"R1 classify: {'success' if r1_code == 0 else ('failed' if r1_code else 'skipped')}")
    print(f"R2 summarize: {'success' if r2_code == 0 else ('failed' if r2_code else 'skipped')}")
    print(f"R3 archive: {'success' if r3_code == 0 else ('failed' if r3_code else 'skipped')}")

    failed = any(code is not None and code != 0 for code in (r0_code, r1_code, r2_code, r3_code))
    if failed:
        logger.error("R4 pipeline finished with failures")
    else:
        logger.info("R4 pipeline finished successfully")
    cleanup_data(config)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
