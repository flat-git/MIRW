"""报告生成器。"""

from __future__ import annotations

import pandas as pd

from src.reporting.llm_client import call_llm_pro
from src.reporting.templates import build_ie_weekly_prompt, build_capa_prompt
from src.reporting.report_checker import check_report


def generate_ie_weekly_report(
    period: str,
    runs_df: pd.DataFrame,
    events_df: pd.DataFrame,
    repeated_issues: list[dict] | None = None,
    action_summary: dict | None = None,
) -> dict:
    """生成 IE 改善复盘周报。

    所有数值由 Python 确定性计算，LLM 只负责报告整理。
    """
    from src.metrics.efficiency import calculate_efficiency_summary
    from src.metrics.pareto import top_loss_pareto

    # 确定性计算
    efficiency = calculate_efficiency_summary(runs_df, events_df)
    pareto = top_loss_pareto(events_df).to_dict("records") if not top_loss_pareto(events_df).empty else []

    # 构建输入 JSON
    data = {
        "report_type": "IE_WEEKLY_REVIEW",
        "period": period,
        "metrics": {
            "total_downtime_min": efficiency.get("total_downtime_min"),
            "line_efficiency": efficiency.get("line_efficiency"),
            "downtime_ratio": efficiency.get("downtime_ratio"),
            "total_runs": efficiency.get("total_runs"),
            "top_loss": [
                {"category": p["category"], "minutes": p["total_downtime_min"], "ratio": p.get("ratio", 0)}
                for p in pareto[:5]
            ],
        },
        "repeated_issues": repeated_issues or [],
        "action_items": action_summary or {},
    }

    # 调用 LLM 生成报告
    messages = build_ie_weekly_prompt(data)
    report_text = call_llm_pro(messages, temperature=0.2)

    # 审核报告
    check_result = check_report(report_text, data)

    return {
        "report_type": "IE_WEEKLY_REVIEW",
        "period": period,
        "report_markdown": report_text,
        "input_data": data,
        "check_result": check_result,
    }


def generate_quality_capa_report(
    period: str,
    runs_df: pd.DataFrame,
    events_df: pd.DataFrame,
    quality_issues: list[dict] | None = None,
    evidence_notes: list[str] | None = None,
) -> dict:
    """生成质量 CAPA 草稿报告。"""
    from src.metrics.quality import quality_related_downtime, scrap_rate

    # 确定性计算
    qdt = quality_related_downtime(events_df)
    sr = scrap_rate(runs_df)

    data = {
        "report_type": "QUALITY_CAPA_DRAFT",
        "period": period,
        "quality_metrics": {
            "quality_related_downtime_min": qdt.get("quality_downtime_min"),
            "scrap_rate": sr.get("scrap_rate"),
            "top_quality_issues": quality_issues or [],
        },
        "evidence_notes": evidence_notes or [],
    }

    # 调用 LLM 生成报告
    messages = build_capa_prompt(data)
    report_text = call_llm_pro(messages, temperature=0.2)

    # 审核报告
    check_result = check_report(report_text, data)

    return {
        "report_type": "QUALITY_CAPA_DRAFT",
        "period": period,
        "report_markdown": report_text,
        "input_data": data,
        "check_result": check_result,
    }
