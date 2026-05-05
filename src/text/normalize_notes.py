"""异常备注标准化：调用 LLM 将原始备注转换为标准类别。"""

from __future__ import annotations

import json
import pandas as pd

from src.config.taxonomy import STANDARD_LOSS_CATEGORIES, QUALITY_LOSS_CATEGORIES, PCBA_SMT_CATEGORIES
from src.reporting.llm_client import call_llm_flash


NORMALIZE_SYSTEM_PROMPT = """你是制造现场异常备注标准化助手。
你只能基于输入中的 raw_reason 和 raw_note 输出结果。
不得编造不存在的设备、物料、人员、批次或原因。
必须从 allowed_categories 中选择 standard_loss_category。
必须给出 evidence_text，且 evidence_text 必须是 raw_note 的原文子串。
如果无法判断，standard_loss_category 输出 Unknown，并标记 needs_review=true。
输出必须是 JSON，格式如下：
{
  "event_id": "...",
  "issue_summary": "...",
  "standard_loss_category": "...",
  "specific_category": "...",
  "responsible_area": "...",
  "confidence": 0.0-1.0,
  "evidence_text": "...",
  "needs_review": true/false
}"""


def normalize_note(event_id: str, raw_reason: str, raw_note: str | None,
                   allowed_categories: list[str] | None = None) -> dict:
    """标准化单条异常备注。

    调用 LLM 进行分类和摘要，然后做后处理校验。
    """
    if allowed_categories is None:
        allowed_categories = STANDARD_LOSS_CATEGORIES

    note_text = raw_note if raw_note else raw_reason

    user_message = json.dumps({
        "event_id": event_id,
        "raw_reason": raw_reason,
        "raw_note": note_text,
        "allowed_categories": allowed_categories,
    }, ensure_ascii=False)

    response_text = call_llm_flash(
        messages=[
            {"role": "system", "content": NORMALIZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )

    # 解析 JSON 响应
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取 JSON
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if match:
            result = json.loads(match.group(1))
        else:
            return {
                "event_id": event_id,
                "issue_summary": raw_reason,
                "standard_loss_category": "Unknown",
                "specific_category": "Unknown",
                "responsible_area": "Unknown",
                "confidence": 0.0,
                "evidence_text": note_text[:50] if note_text else "",
                "needs_review": True,
                "error": "LLM 响应无法解析为 JSON",
            }

    # 后处理校验
    result = _post_validate(result, note_text, allowed_categories)

    return result


def normalize_notes_batch(events_df: pd.DataFrame, allowed_categories: list[str] | None = None) -> pd.DataFrame:
    """批量标准化异常备注。"""
    results = []

    for _, row in events_df.iterrows():
        result = normalize_note(
            event_id=str(row.get("event_id", "")),
            raw_reason=str(row.get("raw_reason", "")),
            raw_note=row.get("raw_note"),
            allowed_categories=allowed_categories,
        )
        results.append(result)

    return pd.DataFrame(results)


def _post_validate(result: dict, raw_note: str, allowed_categories: list[str]) -> dict:
    """后处理校验。"""
    needs_review = result.get("needs_review", False)

    # 1. 检查 category 是否在允许列表中
    category = result.get("standard_loss_category", "Unknown")
    if category not in allowed_categories:
        result["standard_loss_category"] = "Unknown"
        needs_review = True

    # 2. 检查 evidence_text 是否是 raw_note 的子串
    evidence = result.get("evidence_text", "")
    if evidence and raw_note:
        if evidence not in raw_note:
            needs_review = True
            result["evidence_text_error"] = "evidence_text 不是 raw_note 的子串"
    elif not evidence:
        needs_review = True

    # 3. 置信度检查
    confidence = result.get("confidence", 0.0)
    if confidence < 0.65:
        needs_review = True

    result["needs_review"] = needs_review
    return result
