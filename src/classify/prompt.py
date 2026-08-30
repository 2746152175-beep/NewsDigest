"""Build system/user prompts for DeepSeek classification with injected vocabularies."""

import json

from src.config_loader import load_taxonomy, load_watchlist


def load_vocab(watchlist: dict, taxonomy: dict) -> dict:
    """Flatten watchlist companies and taxonomy categories/segments."""
    companies: list[str] = []
    seen: set[str] = set()
    groups = watchlist.get("watchlist") or {}
    for names in groups.values():
        for name in names or []:
            name = str(name).strip()
            if name and name not in seen:
                seen.add(name)
                companies.append(name)
    categories = [str(c).strip() for c in (taxonomy.get("categories") or []) if str(c).strip()]
    segments = [str(s).strip() for s in (taxonomy.get("segments") or []) if str(s).strip()]
    return {"companies": companies, "categories": categories, "segments": segments}


def build_system_prompt(vocab: dict) -> str:
    """Construct the system prompt embedding the classification rules and vocab."""
    companies = "、".join(vocab["companies"]) or "(无)"
    categories = "、".join(vocab["categories"]) or "(无)"
    segments = "、".join(vocab["segments"]) or "(无)"
    return (
        "你是一名科技新闻分析师，专注于美国优秀科技公司的重要消息、技术突破与产业动态。\n"
        "请对每条新闻做相关性判断并归类。\n\n"
        "分类规则：\n"
        "- relevant：是否属于美国优秀科技公司的重要消息（技术/产品/战略/融资/监管/行业趋势/人才/财报等）。"
        "纯八卦、娱乐、社媒口水、纯招聘、重复营销、与科技公司无关的内容判为 false。\n"
        "- company：从观察清单中选出涉及的公司，可多个；若不在清单但明显是重要科技公司，可填具体公司名；不相关则留空数组 []。\n"
        "- category：必须且只能从给定 categories 中单选一个，不能自造。\n"
        "- segment：从给定 segments 中多选，可多个，不能自造。\n"
        "- importance：1-5 整数，5 为最高。\n"
        "- reason：一句话中文理由。\n\n"
        f"可用的公司清单：{companies}\n\n"
        f"可选 category（单选）：{categories}\n\n"
        f"可选 segment（多选）：{segments}\n\n"
        "只输出一个 JSON 对象，不要输出任何多余文字。格式：\n"
        '{"items":[{"id":"原id","relevant":true,"company":["..."],"category":"...",'
        '"segment":["..."],"importance":4,"reason":"..."}]}\n'
        "items 数组必须与输入批次一一对应，id 必须原样保留，不能新增或丢失。"
    )


def build_user_prompt(batch: list[dict]) -> str:
    """Construct the user prompt containing one batch of raw news items."""
    payload = []
    for item in batch:
        payload.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "url": item.get("url"),
                "summary": item.get("summary"),
                "source": item.get("source"),
                "source_type": item.get("source_type"),
                "published_at": item.get("published_at"),
                "author": item.get("author"),
            }
        )
    rendered = json.dumps(payload, ensure_ascii=False)
    return "请对以下新闻批次分类，严格按系统要求返回 JSON 对象：\n" + rendered
