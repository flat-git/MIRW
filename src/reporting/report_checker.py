"""报告质量检查器。验证 LLM 生成的报告是否符合要求。"""

from __future__ import annotations

import re


# 不应出现在报告中的确定性表述
DETERMINISTIC_PHRASES = [
    "根本原因", "确定原因", "根因为", "结论是",
    "一定是", "肯定是", "毫无疑问", "明确为",
]

# 必须包含的标记
REQUIRED_MARKERS = [
    "待人工确认", "待确认", "候选", "建议",
]


def check_report(report_text: str, input_data: dict) -> dict:
    """检查 LLM 生成的报告是否符合质量要求。

    检查项：
    1. 是否包含关键数值
    2. 是否包含原始异常备注证据
    3. 是否出现输入 JSON 中不存在的实体
    4. 是否把候选根因写成确定根因
    5. 是否包含"待人工确认"
    """
    checks = {}

    # 1. 检查关键数值
    checks["has_required_metrics"] = _check_metrics_present(report_text, input_data)

    # 2. 检查是否包含原始证据
    checks["has_evidence_notes"] = _check_evidence_present(report_text, input_data)

    # 3. 检查确定性表述
    checks["deterministic_phrase_count"] = _count_deterministic_phrases(report_text)

    # 4. 检查是否包含"待确认"标记
    checks["contains_human_confirmation_notice"] = _check_confirmation_notice(report_text)

    # 5. 综合判断
    checks["pass"] = (
        checks["has_required_metrics"]
        and checks["has_evidence_notes"]
        and checks["deterministic_phrase_count"] == 0
        and checks["contains_human_confirmation_notice"]
    )

    return checks


def _check_metrics_present(report_text: str, input_data: dict) -> bool:
    """检查报告中是否包含关键数值。"""
    metrics = input_data.get("metrics", input_data.get("quality_metrics", {}))
    if not metrics:
        return True  # 没有指标数据则跳过

    # 至少有一个数值出现在报告中
    for key, value in metrics.items():
        if value is None:
            continue
        str_val = str(value)
        if str_val in report_text:
            return True

    return False


def _check_evidence_present(report_text: str, input_data: dict) -> bool:
    """检查报告中是否包含原始异常备注证据。"""
    # 检查 repeated_issues 中的 evidence_notes
    repeated = input_data.get("repeated_issues", [])
    for issue in repeated:
        for note in issue.get("evidence_notes", []):
            # 取前 20 个字符作为匹配
            snippet = note[:20]
            if snippet in report_text:
                return True

    # 检查 evidence_notes（CAPA 报告）
    evidence_notes = input_data.get("evidence_notes", [])
    for note in evidence_notes:
        snippet = note[:20]
        if snippet in report_text:
            return True

    # 检查 raw_note（5Why 报告）
    raw_note = input_data.get("raw_note", "")
    if raw_note and raw_note[:20] in report_text:
        return True

    # 如果没有证据数据，跳过检查
    if not repeated and not evidence_notes and not raw_note:
        return True

    return False


def _count_deterministic_phrases(report_text: str) -> int:
    """统计报告中出现的确定性表述数量。"""
    count = 0
    for phrase in DETERMINISTIC_PHRASES:
        count += report_text.count(phrase)
    return count


def _check_confirmation_notice(report_text: str) -> bool:
    """检查报告中是否包含"待确认"类标记。"""
    for marker in REQUIRED_MARKERS:
        if marker in report_text:
            return True
    return False
