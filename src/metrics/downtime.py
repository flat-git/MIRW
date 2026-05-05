"""停机损失分析。"""

from __future__ import annotations

import pandas as pd


def downtime_by_category(events_df: pd.DataFrame) -> pd.DataFrame:
    """按损失类别统计停机时间。"""
    if "standard_loss_category" not in events_df.columns:
        # 使用 raw_reason 作为 fallback
        col = "raw_reason"
    else:
        col = "standard_loss_category"

    grouped = events_df.groupby(col, dropna=False).agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    grouped.columns = ["category", "total_downtime_min", "event_count"]
    total = grouped["total_downtime_min"].sum()
    grouped["ratio"] = (grouped["total_downtime_min"] / total).round(4) if total > 0 else 0
    grouped = grouped.sort_values("total_downtime_min", ascending=False)

    return grouped


def downtime_by_product(events_df: pd.DataFrame) -> pd.DataFrame:
    """按产品统计停机时间。"""
    if "product_id" not in events_df.columns:
        return pd.DataFrame(columns=["product_id", "total_downtime_min", "event_count", "ratio"])

    grouped = events_df.groupby("product_id", dropna=False).agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    total = grouped["total_downtime_min"].sum()
    grouped["ratio"] = (grouped["total_downtime_min"] / total).round(4) if total > 0 else 0
    grouped = grouped.sort_values("total_downtime_min", ascending=False)

    return grouped


def downtime_by_shift(events_df: pd.DataFrame) -> pd.DataFrame:
    """按班次统计停机时间。"""
    if "shift" not in events_df.columns:
        return pd.DataFrame(columns=["shift", "total_downtime_min", "event_count", "ratio"])

    grouped = events_df.groupby("shift", dropna=False).agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    total = grouped["total_downtime_min"].sum()
    grouped["ratio"] = (grouped["total_downtime_min"] / total).round(4) if total > 0 else 0
    grouped = grouped.sort_values("total_downtime_min", ascending=False)

    return grouped


def downtime_by_operator(events_df: pd.DataFrame) -> pd.DataFrame:
    """按操作员统计停机时间。"""
    if "operator_id" not in events_df.columns:
        return pd.DataFrame(columns=["operator_id", "total_downtime_min", "event_count", "ratio"])

    grouped = events_df.groupby("operator_id", dropna=False).agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    total = grouped["total_downtime_min"].sum()
    grouped["ratio"] = (grouped["total_downtime_min"] / total).round(4) if total > 0 else 0
    grouped = grouped.sort_values("total_downtime_min", ascending=False)

    return grouped


def downtime_by_machine(events_df: pd.DataFrame) -> pd.DataFrame:
    """按设备统计停机时间。"""
    if "machine_id" not in events_df.columns:
        return pd.DataFrame(columns=["machine_id", "total_downtime_min", "event_count", "ratio"])

    grouped = events_df.groupby("machine_id", dropna=False).agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    total = grouped["total_downtime_min"].sum()
    grouped["ratio"] = (grouped["total_downtime_min"] / total).round(4) if total > 0 else 0
    grouped = grouped.sort_values("total_downtime_min", ascending=False)

    return grouped
