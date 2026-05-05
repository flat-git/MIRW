"""5Why 分析草稿生成器。"""

from __future__ import annotations

from src.reporting.llm_client import call_llm_pro
from src.reporting.templates import build_five_why_prompt
from src.reporting.report_checker import check_report


def generate_five_why(
    event_id: str,
    raw_reason: str,
    raw_note: str | None,
    downtime_min: float,
    similar_events: list[dict] | None = None,
) -> dict:
    """生成单个异常事件的 5Why 分析草稿。"""
    data = {
        "event_id": event_id,
        "raw_reason": raw_reason,
        "raw_note": raw_note or raw_reason,
        "downtime_min": downtime_min,
        "similar_events": similar_events or [],
    }

    messages = build_five_why_prompt(data)
    report_text = call_llm_pro(messages, temperature=0.2)

    check_result = check_report(report_text, data)

    return {
        "report_type": "FIVE_WHY_DRAFT",
        "event_id": event_id,
        "report_markdown": report_text,
        "input_data": data,
        "check_result": check_result,
    }
