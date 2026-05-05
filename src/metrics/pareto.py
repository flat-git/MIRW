"""Pareto 分析。"""

from __future__ import annotations

import pandas as pd


def top_loss_pareto(events_df: pd.DataFrame, group_col: str = "standard_loss_category", top_n: int = 10) -> pd.DataFrame:
    """计算 Top Loss Pareto 数据。

    返回按停机时间降序排列的 DataFrame，包含累计比率。
    """
    if group_col not in events_df.columns:
        # fallback 到 raw_reason
        group_col = "raw_reason"

    if group_col not in events_df.columns:
        return pd.DataFrame()

    grouped = events_df.groupby(group_col, dropna=False).agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    grouped.columns = ["category", "total_downtime_min", "event_count"]
    grouped = grouped.sort_values("total_downtime_min", ascending=False).head(top_n)

    grand_total = grouped["total_downtime_min"].sum()
    if grand_total > 0:
        grouped["ratio"] = (grouped["total_downtime_min"] / grand_total).round(4)
        grouped["cumulative_ratio"] = grouped["ratio"].cumsum().round(4)
    else:
        grouped["ratio"] = 0.0
        grouped["cumulative_ratio"] = 0.0

    grouped = grouped.reset_index(drop=True)
    grouped.index = grouped.index + 1  # 1-based ranking
    grouped.index.name = "rank"

    return grouped


def pareto_chart_data(events_df: pd.DataFrame, group_col: str = "standard_loss_category", top_n: int = 10) -> dict:
    """生成 Pareto 图表数据（适配 Plotly）。"""
    pareto_df = top_loss_pareto(events_df, group_col, top_n)

    if pareto_df.empty:
        return {"categories": [], "values": [], "cumulative_ratios": []}

    return {
        "categories": pareto_df["category"].tolist(),
        "values": pareto_df["total_downtime_min"].tolist(),
        "ratios": pareto_df["ratio"].tolist(),
        "cumulative_ratios": pareto_df["cumulative_ratio"].tolist(),
        "counts": pareto_df["event_count"].tolist(),
    }
