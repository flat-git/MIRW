"""报告生成服务。调用 src/reporting 生成。"""

from __future__ import annotations

import pandas as pd

from backend.state import store
from src.reporting.report_generator import generate_ie_weekly_report, generate_quality_capa_report
from src.reporting.five_why_generator import generate_five_why
from src.metrics.efficiency import calculate_efficiency_summary
from src.metrics.pareto import top_loss_pareto
from src.metrics.downtime import downtime_by_category, downtime_by_product, downtime_by_operator, downtime_by_machine
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
    report = {
        "report_type": "IE_WEEKLY_REVIEW",
        "period": period,
        "report_markdown": result["report_markdown"],
        "check_result": result["check_result"],
    }
    store.store_report(dataset_id, report.copy())
    return report


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
    report = {
        "report_type": "QUALITY_CAPA_DRAFT",
        "period": period,
        "report_markdown": result["report_markdown"],
        "check_result": result["check_result"],
    }
    store.store_report(dataset_id, report.copy())
    return report


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


def generate_analysis_report(dataset_id: str) -> str:
    """生成数据分析 markdown 报告（纯 Python，不调 LLM）。"""
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    runs_df = ds["runs_df"]
    events_df = ds["events_df"]
    validation = ds.get("validation", {})
    capability = validation.get("capability", {})

    lines = []
    lines.append(f"# 数据分析报告 — {ds['source']}")
    lines.append("")

    # 数据概览
    lines.append("## 数据概览")
    lines.append(f"- 数据集 ID: `{dataset_id}`")
    lines.append(f"- 数据源: {ds['source']}")
    lines.append(f"- 生产批次: {len(runs_df)}")
    lines.append(f"- 停机事件: {len(events_df)}")
    runs_passed = validation.get("production_runs", {}).get("passed", False)
    events_passed = validation.get("downtime_events", {}).get("passed", False)
    lines.append(f"- 数据校验: {'✅ 通过' if runs_passed and events_passed else '❌ 未通过'}")
    lines.append("")

    # 效率指标
    eff = calculate_efficiency_summary(runs_df, events_df)
    lines.append("## 效率指标")
    lines.append(f"- 总停机时间: {eff.get('total_downtime_min', 'N/A')} min")
    dt_ratio = eff.get("downtime_ratio")
    lines.append(f"- 停机比率: {dt_ratio:.1%}" if dt_ratio else "- 停机比率: N/A")
    line_eff = eff.get("line_efficiency")
    lines.append(f"- 产线效率: {line_eff:.1%}" if line_eff else "- 产线效率: N/A")
    lines.append("")

    # Top Loss Pareto
    pareto = top_loss_pareto(events_df, top_n=10)
    if not pareto.empty:
        lines.append("## Top Loss Pareto")
        lines.append("")
        lines.append("| 排名 | 损失类别 | 停机时间(min) | 占比 | 累计占比 |")
        lines.append("|------|---------|-------------|------|---------|")
        for _, row in pareto.iterrows():
            rank = row.get("rank", "")
            lines.append(
                f"| {rank} | {row['category']} | {row['total_downtime_min']:.0f} | "
                f"{row['ratio']:.1%} | {row['cumulative_ratio']:.1%} |"
            )
        lines.append("")

    # 分组分析
    for label, fn, key in [
        ("按产品", downtime_by_product, "product_id"),
        ("按操作员", downtime_by_operator, "operator_id"),
        ("按设备", downtime_by_machine, "machine_id"),
    ]:
        grouped = fn(events_df)
        if not grouped.empty:
            lines.append(f"## {label}")
            lines.append("")
            lines.append(f"| {key} | 停机时间(min) | 事件数 | 占比 |")
            lines.append("|------|-------------|--------|------|")
            for _, row in grouped.head(10).iterrows():
                lines.append(
                    f"| {row[key]} | {row['total_downtime_min']:.0f} | "
                    f"{int(row['event_count'])} | {row['ratio']:.1%} |"
                )
            lines.append("")

    # 能力检测
    lines.append("## 能力检测")
    lines.append("")
    for k, v in capability.items():
        if k == "missing_fields":
            continue
        icon = "✅" if v else "❌"
        lines.append(f"- {icon} {k}")
    missing = capability.get("missing_fields", [])
    if missing:
        lines.append(f"- 缺少字段: {', '.join(missing)}")
    lines.append("")

    return "\n".join(lines)
