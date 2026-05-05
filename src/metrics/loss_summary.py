"""综合损失汇总。"""

from __future__ import annotations

import pandas as pd

from src.metrics.efficiency import calculate_efficiency_summary
from src.metrics.downtime import downtime_by_category
from src.metrics.pareto import top_loss_pareto


def generate_loss_summary(runs_df: pd.DataFrame, events_df: pd.DataFrame) -> dict:
    """生成综合损失摘要，用于 IE 周报输入。"""
    # 效率指标
    efficiency = calculate_efficiency_summary(runs_df, events_df)

    # Top Loss Pareto
    pareto = top_loss_pareto(events_df)

    # 按类别
    by_category = downtime_by_category(events_df)

    # 重复事件统计（按 raw_reason 聚合）
    repeated = _find_repeated_issues(events_df)

    return {
        "efficiency": efficiency,
        "pareto": pareto.to_dict("records") if not pareto.empty else [],
        "by_category": by_category.to_dict("records") if not by_category.empty else [],
        "repeated_issues": repeated,
    }


def _find_repeated_issues(events_df: pd.DataFrame, min_count: int = 2) -> list[dict]:
    """找出重复发生的异常（按 raw_reason 聚合）。"""
    if "raw_reason" not in events_df.columns:
        return []

    grouped = events_df.groupby("raw_reason").agg(
        count=("event_id", "count"),
        total_downtime_min=("downtime_min", "sum"),
        event_ids=("event_id", list),
    ).reset_index()

    repeated = grouped[grouped["count"] >= min_count].sort_values("count", ascending=False)

    result = []
    for _, row in repeated.iterrows():
        # 获取相关备注
        notes = []
        if "raw_note" in events_df.columns:
            related = events_df[events_df["raw_reason"] == row["raw_reason"]]
            notes = related["raw_note"].dropna().tolist()[:3]

        result.append({
            "issue_summary": row["raw_reason"],
            "count": int(row["count"]),
            "cumulative_downtime_min": float(row["total_downtime_min"]),
            "evidence_notes": notes,
        })

    return result
