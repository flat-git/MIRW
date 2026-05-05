"""报告生成服务。调用 src/reporting 生成。"""

from __future__ import annotations

import pandas as pd

from backend.state import store
from src.reporting.report_generator import generate_ie_weekly_report, generate_quality_capa_report
from src.reporting.five_why_generator import generate_five_why
from src.metrics.loss_summary import _find_repeated_issues
from src.metrics.quality import quality_issue_pareto


def generate_ie_weekly(dataset_id: str, period: str) -> dict:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    runs_df = ds["runs_df"] if len(ds["runs_df"]) > 0 else pd.DataFrame()
    events_df = ds["events_df"]
    repeated = _find_repeated_issues(events_df)

    result = generate_ie_weekly_report(
        period=period, runs_df=runs_df, events_df=events_df,
        repeated_issues=repeated, action_summary=None,
    )
    return {
        "report_type": "IE_WEEKLY_REVIEW",
        "period": period,
        "report_markdown": result["report_markdown"],
        "check_result": result["check_result"],
    }


def generate_capa(dataset_id: str, period: str) -> dict:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    runs_df = ds["runs_df"] if len(ds["runs_df"]) > 0 else pd.DataFrame()
    events_df = ds["events_df"]

    qpareto = quality_issue_pareto(events_df)
    quality_issues = qpareto.to_dict("records") if not qpareto.empty else []
    evidence = events_df["raw_note"].dropna().head(5).tolist() if "raw_note" in events_df.columns else []

    result = generate_quality_capa_report(
        period=period, runs_df=runs_df, events_df=events_df,
        quality_issues=quality_issues, evidence_notes=evidence,
    )
    return {
        "report_type": "QUALITY_CAPA_DRAFT",
        "period": period,
        "report_markdown": result["report_markdown"],
        "check_result": result["check_result"],
    }


def generate_five_why_report(dataset_id: str, event_id: str) -> dict:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    events_df = ds["events_df"]
    matched = events_df[events_df["event_id"] == event_id]
    if matched.empty:
        raise ValueError(f"事件 {event_id} 不存在")

    row = matched.iloc[0]
    result = generate_five_why(
        event_id=event_id,
        raw_reason=str(row.get("raw_reason", "")),
        raw_note=row.get("raw_note"),
        downtime_min=float(row.get("downtime_min", 0)),
    )
    return {
        "report_type": "FIVE_WHY_DRAFT",
        "period": "",
        "report_markdown": result["report_markdown"],
        "check_result": result["check_result"],
    }
