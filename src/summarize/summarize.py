"""R2 entry point: DeepSeek summarization + industry insight."""

import argparse
import difflib
import json
import logging
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from src.config_loader import load_config, resolve_path
from src.scheduler.log import setup_logging
from src.summarize.fetch_body import fetch_body
from src.summarize.prompt import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

_client: OpenAI | None = None
_client_signature: tuple | None = None


def _api_key(config: dict) -> str:
    env_name = config["llm"]["api_key_env"]
    key = os.environ.get(env_name, "").strip()
    if not key:
        raise RuntimeError(f"LLM 环境变量 '{env_name}' 未设置或为空")
    return key


def _get_client(config: dict) -> OpenAI:
    """Return a cached OpenAI client configured from config.yaml, never hardcoded."""
    global _client, _client_signature
    llm = config["llm"]
    api_key = _api_key(config)
    signature = (llm.get("base_url"), llm.get("model"), llm.get("timeout"), api_key)
    if _client is None or _client_signature != signature:
        _client = OpenAI(
            api_key=api_key,
            base_url=llm.get("base_url"),
            timeout=llm.get("timeout", 60),
            max_retries=0,
        )
        _client_signature = signature
    return _client


def _is_chinese(text: str) -> bool:
    """Return True when text is non-empty and contains at least one CJK character."""
    return bool(text) and bool(_CJK_RE.search(text))


def _normalize_title(title: str) -> str:
    """Lowercase and strip non-alphanumeric characters for similarity comparison."""
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def _filter_relevant(items: list[dict], config: dict) -> list[dict]:
    """Apply relevance, importance, segment, and similar-title filters in order."""
    filter_cfg = config.get("filter") or {}
    importance_min = int(filter_cfg.get("importance_min", 0) or 0)
    selected_segments = set(filter_cfg.get("segments") or [])

    kept: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("relevant") is not True:
            continue
        importance = int(it.get("importance") or 0)
        if importance_min and importance < importance_min:
            continue
        if selected_segments:
            raw_segments = it.get("segment") or []
            if isinstance(raw_segments, str):
                raw_segments = [raw_segments]
            if not set(raw_segments).intersection(selected_segments):
                continue
        kept.append(it)

    deduped: list[dict] = []
    seen_norms: list[str] = []
    ordered = sorted(
        kept,
        key=lambda it: (int(it.get("importance") or 0), it.get("published_at") or ""),
        reverse=True,
    )
    for it in ordered:
        norm = _normalize_title(it.get("title"))
        if not norm:
            deduped.append(it)
            continue
        if any(difflib.SequenceMatcher(None, norm, seen).ratio() > 0.8 for seen in seen_norms):
            continue
        deduped.append(it)
        seen_norms.append(norm)

    return deduped


def _fallback_record(item: dict) -> dict:
    """A deterministic Chinese placeholder used when the LLM cannot summarize."""
    return {
        "id": item.get("id"),
        "summary": "本条新闻的自动概括未能生成，请参考原文。",
        "insight": "暂未生成产业启示，需人工结合行业背景补充分析。",
        "key_points": [],
    }


def _coerce_record(record: dict, item: dict) -> dict:
    """Normalize one LLM result while preserving the input item id."""
    summary = str(record.get("summary") or "").strip()
    insight = str(record.get("insight") or "").strip()
    points = record.get("key_points") or []
    if not isinstance(points, list):
        points = [points]
    points = [str(p).strip() for p in points if str(p).strip()]
    return {
        "id": item.get("id"),
        "summary": summary,
        "insight": insight,
        "key_points": points,
    }


def summarize_batch(
    items: list[dict],
    config: dict,
    client: OpenAI | None = None,
) -> list[dict]:
    """Summarize one batch with retries; never raises, falls back per item."""
    if not items:
        return []

    llm = config["llm"]
    max_retries = int(llm.get("max_retries") or 0)
    backoff = float(llm.get("retry_backoff") or 2.0)
    attempts = max_retries + 1
    active_client = client or _get_client(config)
    system = build_system_prompt()
    user = build_user_prompt(items)

    def finalize(record: dict, ok: bool) -> dict:
        return {**record, "_ok": bool(ok)}

    for attempt in range(1, attempts + 1):
        try:
            create_kwargs: dict = {}
            if llm.get("json_mode", True):
                create_kwargs["response_format"] = {"type": "json_object"}
            if llm.get("temperature") is not None:
                create_kwargs["temperature"] = llm["temperature"]
            response = active_client.chat.completions.create(
                model=llm["model"],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **create_kwargs,
            )
            content = response.choices[0].message.content or ""
            data = json.loads(content)
            raw_items = data.get("items", []) if isinstance(data, dict) else []
            if not isinstance(raw_items, list):
                raise ValueError("LLM 返回的 items 不是数组")

            by_id: dict[str, dict] = {}
            for rec in raw_items:
                if isinstance(rec, dict) and rec.get("id"):
                    by_id[str(rec["id"])] = rec

            out: list[dict] = []
            all_ok = True
            for item in items:
                rec = by_id.get(item.get("id"))
                if rec is None:
                    logger.warning("batch result missing id %s (attempt %d)", item.get("id"), attempt)
                    all_ok = False
                    out.append(finalize(_fallback_record(item), False))
                    continue
                coerced = _coerce_record(rec, item)
                ok = _is_chinese(coerced["summary"]) and _is_chinese(coerced["insight"])
                if ok:
                    out.append(finalize(coerced, True))
                else:
                    logger.warning(
                        "invalid summary/insight for id %s (attempt %d)",
                        item.get("id"),
                        attempt,
                    )
                    all_ok = False
                    out.append(finalize(_fallback_record(item), False))

            if all_ok:
                return out
            if attempt < attempts:
                logger.warning(
                    "summarize batch attempt %d/%d has missing or non-Chinese items, retrying",
                    attempt,
                    attempts,
                )
                time.sleep(backoff * attempt)
                continue
            return out
        except Exception as exc:
            if attempt < attempts:
                logger.warning("summarize batch attempt %d/%d failed: %s", attempt, attempts, exc)
                time.sleep(backoff * attempt)
            else:
                logger.exception("summarize batch failed after %d attempts", attempts)

    return [finalize(_fallback_record(item), False) for item in items]


def _chunks(items: list[dict], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R2: DeepSeek summarization + insight")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today (Asia/Shanghai)")
    parser.add_argument("--batch-size", type=int, default=None, help="override batch size (default 8)")
    args = parser.parse_args(argv)

    config = load_config()
    setup_logging(config)

    timezone_name = (config.get("project") or {}).get("timezone") or "Asia/Shanghai"
    tz = ZoneInfo(timezone_name)
    date_str = args.date or datetime.now(tz).date().isoformat()

    classified_dir = resolve_path((config.get("data") or {}).get("classified_dir") or "data/classified")
    summarized_dir = resolve_path((config.get("data") or {}).get("summarized_dir") or "data/summarized")
    classified_path = classified_dir / f"{date_str}.json"

    if not classified_path.exists():
        logger.error("classified file not found: %s", classified_path)
        print(f"[R2] error: classified file not found: {classified_path}")
        return 1

    with open(classified_path, "r", encoding="utf-8") as fh:
        items = json.load(fh)
    if not isinstance(items, list):
        logger.error("classified file is not a list: %s", classified_path)
        print(f"[R2] error: classified file is not a list: {classified_path}")
        return 1

    relevant = _filter_relevant(items, config)

    if not relevant:
        summarized_dir.mkdir(parents=True, exist_ok=True)
        out_path = summarized_dir / f"{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump([], fh, ensure_ascii=False, indent=2)
        print("[R2] relevant: 0")
        print("[R2] body fetched: 0")
        print("[R2] summarized: 0")
        print(f"[R2] output: {out_path}")
        return 0

    try:
        client = _get_client(config)
    except Exception as exc:
        logger.error("failed to initialize LLM client: %s", exc)
        print(f"[R2] error: LLM client init failed: {exc}")
        return 1

    item_by_id = {it["id"]: it for it in relevant}
    prepared: list[dict] = []
    body_ok_count = 0
    for it in relevant:
        body = fetch_body(it.get("url") or "")
        if body:
            body_ok_count += 1
        content = body or (it.get("summary") or "").strip() or (it.get("title") or "").strip()
        prepared.append({**it, "body": content})

    configured_batch = int((config.get("summarize") or {}).get("batch_size", 8))
    batch_size = args.batch_size or configured_batch
    if batch_size <= 0:
        batch_size = 8

    out: list[dict] = []
    ok_count = 0
    for batch in _chunks(prepared, batch_size):
        results = summarize_batch(batch, config, client=client)
        for res in results:
            ok = bool(res.pop("_ok", False))
            original = item_by_id.get(res.get("id"))
            if original is None:
                logger.error("result id not found in input: %s", res.get("id"))
                continue
            if ok:
                ok_count += 1
            out.append(
                {
                    **original,
                    "summary": res.get("summary", ""),
                    "insight": res.get("insight", ""),
                    "key_points": res.get("key_points", []),
                }
            )

    in_ids = [it.get("id") for it in relevant]
    out_ids = [rec.get("id") for rec in out]
    aligned = (
        len(out) == len(relevant)
        and len(set(out_ids)) == len(out_ids)
        and set(out_ids) == set(in_ids)
    )
    if not aligned:
        logger.error("id alignment mismatch: in=%d out=%d", len(in_ids), len(out_ids))
        print("[R2] error: id 对齐失败")
        return 1

    if ok_count == 0:
        logger.error("no item was summarized successfully; aborting without writing output")
        print("[R2] error: 没有任何条目概括成功，未写出输出（请检查 API key / 模型名 / 端点）")
        return 1

    summarized_dir.mkdir(parents=True, exist_ok=True)
    out_path = summarized_dir / f"{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    logger.info(
        "R2 finished: relevant=%d body_ok=%d summarized=%d file=%s",
        len(relevant),
        body_ok_count,
        ok_count,
        out_path,
    )
    print(f"[R2] relevant: {len(relevant)}")
    print(f"[R2] body fetched: {body_ok_count}")
    print(f"[R2] summarized: {ok_count}")
    print(f"[R2] output: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
