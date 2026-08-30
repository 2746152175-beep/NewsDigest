"""R1 entry point: DeepSeek relevance filtering + classification."""

import argparse
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.classify.deepseek_client import MISSING_REASON, classify_batch, fallback_record
from src.classify.prompt import load_vocab
from src.config_loader import (
    load_config,
    load_sources,
    load_taxonomy,
    load_watchlist,
    resolve_path,
)
from src.scheduler.log import setup_logging

logger = logging.getLogger(__name__)

CLASS_FIELDS = ["relevant", "company", "category", "segment", "importance", "reason"]


def _chunks(items: list[dict], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R1: DeepSeek relevance + classification")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today (Asia/Shanghai)")
    parser.add_argument("--batch-size", type=int, default=None, help="override config batch_size")
    args = parser.parse_args(argv)

    config = load_config()
    load_sources()
    watchlist = load_watchlist()
    taxonomy = load_taxonomy()
    setup_logging(config)

    timezone_name = (config.get("project") or {}).get("timezone") or "Asia/Shanghai"
    tz = ZoneInfo(timezone_name)
    date_str = args.date or datetime.now(tz).date().isoformat()

    raw_dir = resolve_path((config.get("data") or {}).get("raw_dir") or "data/raw")
    classified_dir = resolve_path((config.get("data") or {}).get("classified_dir") or "data/classified")
    classified_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{date_str}.json"

    if not raw_path.exists():
        logger.error("raw file not found: %s", raw_path)
        print(f"[R1] error: raw file not found: {raw_path}")
        return 1
    with open(raw_path, "r", encoding="utf-8") as fh:
        items = json.load(fh)
    if not isinstance(items, list) or not items:
        logger.error("raw file is empty or not a list: %s", raw_path)
        print(f"[R1] error: raw file is empty or not a list: {raw_path}")
        return 1

    vocab = load_vocab(watchlist, taxonomy)
    configured_batch = int((config.get("classify") or {}).get("batch_size", 25))
    batch_size = args.batch_size or configured_batch

    out: list[dict] = []
    ok_count = 0
    missing_items: list[tuple[int, dict]] = []
    for batch in _chunks(items, batch_size):
        try:
            results = classify_batch(batch, config, vocab)
        except Exception as exc:
            logger.error("batch failed after retries: %s", exc)
            print(f"[R1] warning: batch of {len(batch)} failed, fallback used: {exc}")
            out.extend(fallback_record(item, "批次分类失败") for item in batch)
            continue
        by_id = {r["id"]: r for r in (results or [])}
        for item in batch:
            record = by_id.get(item["id"])
            if record is None or record.get("reason") == MISSING_REASON:
                missing_items.append((len(out), item))
                out.append(fallback_record(item, MISSING_REASON))
            else:
                ok_count += 1
                out.append({**item, **record})

    in_ids = [it.get("id") for it in items]
    out_ids = [rec.get("id") for rec in out]
    aligned = (
        len(out) == len(items)
        and len(set(out_ids)) == len(out_ids)
        and set(out_ids) == set(in_ids)
    )
    if not aligned:
        logger.error("id alignment mismatch: in=%d out=%d", len(in_ids), len(out_ids))
        print("[R1] error: id 对齐失败")
        return 1

    # 二次重分类：把第一次漏返回的 id 单独再分类一次，避免静默降级丢弃。
    if missing_items:
        logger.info("secondary reclassification for %d missing ids", len(missing_items))
        missing_original = [item for _, item in missing_items]
        try:
            results2 = classify_batch(missing_original, config, vocab)
        except Exception as exc:
            logger.error("secondary reclassification failed: %s", exc)
            results2 = []
        by_id2 = {r["id"]: r for r in (results2 or [])}
        still_missing: list[str] = []
        for idx, item in missing_items:
            record2 = by_id2.get(item["id"])
            if record2 is None or record2.get("reason") == MISSING_REASON:
                still_missing.append(item["id"])
                logger.warning("二次重分类后仍缺失 id %s，保留 fallback", item["id"])
            else:
                ok_count += 1
                out[idx] = {**item, **record2}
        if still_missing:
            logger.warning("二次重分类后仍有 %d 条缺失: %s", len(still_missing), still_missing)
        else:
            logger.info("secondary reclassification recovered all missing ids")

    if items and ok_count == 0:
        logger.error("no batch was successfully classified; aborting without writing output")
        print("[R1] error: 没有任何批次分类成功，未写出输出（请检查 API key / 模型名 / 端点）")
        return 1

    out_path = classified_dir / f"{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    total = len(out)
    relevant = sum(1 for r in out if r.get("relevant"))
    irrelevant = total - relevant
    category_counter = Counter(r.get("category", "") for r in out)
    category_counts = ", ".join(f"{k}={v}" for k, v in sorted(category_counter.items()))

    logger.info(
        "R1 finished: total=%d relevant=%d irrelevant=%d file=%s",
        total,
        relevant,
        irrelevant,
        out_path,
    )
    print(f"[R1] total: {total}")
    print(f"[R1] relevant: {relevant}")
    print(f"[R1] irrelevant: {irrelevant}")
    print(f"[R1] category counts: {category_counts}")
    print(f"[R1] output: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
