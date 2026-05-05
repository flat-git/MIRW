"""IE 生产效率指标。"""

from __future__ import annotations

import pandas as pd


def calculate_downtime_ratio(runs_df: pd.DataFrame) -> dict:
    """计算总体停机比率。

    Downtime Ratio = Total Downtime / Total Planned Time
    """
    if "planned_time_min" not in runs_df.columns or "downtime_min" not in runs_df.columns:
        return {"downtime_ratio": None, "reason": "缺少 planned_time_min 或 downtime_min 字段"}

    total_planned = runs_df["planned_time_min"].sum()
    total_downtime = runs_df["downtime_min"].sum()

    if total_planned <= 0:
        return {"downtime_ratio": None, "reason": "planned_time_min 总和为 0"}

    return {
        "downtime_ratio": round(total_downtime / total_planned, 4),
        "total_planned_min": total_planned,
        "total_downtime_min": total_downtime,
    }


def calculate_line_efficiency(runs_df: pd.DataFrame) -> dict:
    """计算产线效率。

    Line Efficiency = Total Runtime / Total Planned Time
    """
    if "planned_time_min" not in runs_df.columns or "runtime_min" not in runs_df.columns:
        return {"line_efficiency": None, "reason": "缺少 planned_time_min 或 runtime_min 字段"}

    total_planned = runs_df["planned_time_min"].sum()
    total_runtime = runs_df["runtime_min"].sum()

    if total_planned <= 0:
        return {"line_efficiency": None, "reason": "planned_time_min 总和为 0"}

    return {
        "line_efficiency": round(total_runtime / total_planned, 4),
        "total_planned_min": total_planned,
        "total_runtime_min": total_runtime,
    }


def calculate_efficiency_summary(runs_df: pd.DataFrame, events_df: pd.DataFrame | None = None) -> dict:
    """计算综合效率摘要。"""
    summary = {}

    # 基本指标
    summary["total_runs"] = len(runs_df)

    if "planned_time_min" in runs_df.columns:
        summary["total_planned_min"] = float(runs_df["planned_time_min"].sum())

    if "runtime_min" in runs_df.columns:
        summary["total_runtime_min"] = float(runs_df["runtime_min"].sum())

    if "downtime_min" in runs_df.columns:
        summary["total_downtime_min"] = float(runs_df["downtime_min"].sum())
    elif events_df is not None and "downtime_min" in events_df.columns:
        summary["total_downtime_min"] = float(events_df["downtime_min"].sum())

    # 比率
    downtime = calculate_downtime_ratio(runs_df)
    summary["downtime_ratio"] = downtime.get("downtime_ratio")

    efficiency = calculate_line_efficiency(runs_df)
    summary["line_efficiency"] = efficiency.get("line_efficiency")

    return summary
