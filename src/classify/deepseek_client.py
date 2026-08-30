"""DeepSeek (OpenAI-compatible) classification client with JSON mode and retry."""

import json
import logging
import os
import time

from openai import OpenAI

from src.classify.prompt import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

MISSING_REASON = "LLM 返回缺失该条目"

_client: OpenAI | None = None
_client_signature: tuple | None = None


def _api_key(config: dict) -> str:
    env_name = config["llm"]["api_key_env"]
    key = os.environ.get(env_name, "").strip()
    if not key:
        raise RuntimeError(f"LLM 环境变量 '{env_name}' 未设置或为空")
    return key


def get_client(config: dict) -> OpenAI:
    """Return a cached OpenAI client configured from config.yaml, never hardcoded."""
    global _client, _client_signature
    llm = config["llm"]
    api_key = _api_key(config)
    signature = (llm.get("base_url"), llm.get("model"), llm.get("timeout"), api_key)
    if _client is None or signature != _client_signature:
        _client = OpenAI(
            api_key=api_key,
            base_url=llm.get("base_url"),
            timeout=llm.get("timeout", 60),
            max_retries=0,
        )
        _client_signature = signature
    return _client


def fallback_record(item: dict, reason: str) -> dict:
    """A deterministic record used when a batch cannot be classified by the LLM."""
    return {
        "id": item.get("id"),
        "relevant": False,
        "company": [],
        "category": "",
        "segment": [],
        "importance": 1,
        "reason": reason or "分类失败",
    }


def _coerce(record: dict, item: dict, vocab: dict) -> dict:
    """Constrain an LLM record to the allowed vocabularies and value ranges."""
    categories = set(vocab["categories"])
    segments = set(vocab["segments"])

    category = record.get("category")
    if isinstance(category, str) and category.strip():
        if category not in categories:
            logger.warning("category not in vocab for %s: %r -> ''", item.get("id"), category)
            category = ""
    else:
        category = ""

    segs = record.get("segment") or []
    if not isinstance(segs, list):
        segs = [segs]
    segs = [s for s in segs if isinstance(s, str) and s in segments]

    comp = record.get("company") or []
    if not isinstance(comp, list):
        comp = [comp]
    comp = [c for c in comp if isinstance(c, str) and c.strip()]

    try:
        importance = int(record.get("importance"))
    except (TypeError, ValueError):
        importance = 1
    importance = max(1, min(5, importance))

    return {
        "id": item.get("id"),
        "relevant": bool(record.get("relevant", False)),
        "company": comp,
        "category": category,
        "segment": segs,
        "importance": importance,
        "reason": str(record.get("reason") or ""),
    }


def classify_batch(
    items: list[dict],
    config: dict,
    vocab: dict,
    client: OpenAI | None = None,
) -> list[dict]:
    """Classify one batch; retries per llm.max_retries, logs failures per attempt."""
    if not items:
        return []

    llm = config["llm"]
    max_retries = int(llm.get("max_retries") or 0)
    backoff = float(llm.get("retry_backoff") or 2.0)
    attempts = max_retries + 1
    active_client = client or get_client(config)
    system = build_system_prompt(vocab)
    user = build_user_prompt(items)
    last_error = None

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
            by_id = {rec["id"]: rec for rec in raw_items if isinstance(rec, dict) and rec.get("id")}
            out: list[dict] = []
            for item in items:
                record = by_id.get(item.get("id"))
                if record is None:
                    logger.warning("batch result missing id %s", item.get("id"))
                    out.append(fallback_record(item, MISSING_REASON))
                else:
                    out.append(_coerce(record, item, vocab))
            return out
        except Exception as exc:
            last_error = exc
            logger.warning("classify batch attempt %d/%d failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(backoff * attempt)

    raise RuntimeError(f"分类批次在 {attempts} 次尝试后仍失败: {last_error}")
