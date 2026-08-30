"""Build system/user prompts for DeepSeek summarization."""

import json


def build_system_prompt() -> str:
    """Construct the system prompt describing the three required output fields."""
    return (
        "你是一名资深科技产业分析师，专注于美国优秀科技公司的重要新闻。\n"
        "请对每条新闻生成三项内容，全部使用中文：\n"
        "- summary：内容概括。客观、简洁地说明这条新闻讲了什么，不掺杂评价、预测或立场。\n"
        "- insight：内容总结/产业启示。结合产业趋势、竞争格局、技术影响，"
        "说明这条新闻意味着什么、对产业趋势分析有什么价值。\n"
        "- key_points：要点列表，2-5 条，每条一句话，中文。\n\n"
        "要求：\n"
        "- summary 必须客观，与 insight 明显区分，不要重复或互相替代。\n"
        "- summary 与 insight 必须是完整的中文句子；即使原文是英文，也必须翻译并概括为中文，"
        "禁止整句使用英文。人名、公司名、产品名等专有名词可保留英文。\n"
        "- 只输出一个 JSON 对象，不要输出 Markdown、注释或任何多余文字。\n"
        '格式：{"items":[{"id":"原id","summary":"...","insight":"...","key_points":["...","..."]}]}\n'
        "items 数组必须与输入批次一一对应，id 必须原样保留，不能新增或丢失。"
    )


def build_user_prompt(batch: list[dict]) -> str:
    """Construct the user prompt containing one batch of news items with body text."""
    payload = []
    for item in batch:
        payload.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "source": item.get("source"),
                "published_at": item.get("published_at"),
                "body": item.get("body") or "",
            }
        )
    rendered = json.dumps(payload, ensure_ascii=False)
    return "请对以下新闻批次做概括总结，严格按系统要求返回 JSON 对象：\n" + rendered
