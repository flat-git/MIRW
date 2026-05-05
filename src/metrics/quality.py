"""质量相关指标。"""

from __future__ import annotations

import pandas as pd


def scrap_rate(runs_df: pd.DataFrame) -> dict:
    """计算废品率。

    Scrap Rate = Scrap Output / Actual Output
    """
    if "scrap_output" not in runs_df.columns or "actual_output" not in runs_df.columns:
        return {"scrap_rate": None, "reason": "缺少 scrap_output 或 actual_output 字段"}

    total_actual = runs_df["actual_output"].sum()
    total_scrap = runs_df["scrap_output"].sum()

    if total_actual <= 0:
        return {"scrap_rate": None, "reason": "actual_output 总和为 0"}

    return {
        "scrap_rate": round(total_scrap / total_actual, 4),
        "total_scrap": total_scrap,
        "total_actual": total_actual,
    }


def quality_related_downtime(events_df: pd.DataFrame) -> dict:
    """统计质量相关停机。"""
    if "standard_loss_category" in events_df.columns:
        quality_events = events_df[events_df["standard_loss_category"] == "Quality"]
    elif "raw_reason" in events_df.columns:
        # 使用关键词匹配
        quality_keywords = ["quality", "defect", "scrap", "rework", "quality check", "quality defect", "质量"]
        mask = events_df["raw_reason"].str.lower().apply(
            lambda x: any(kw in str(x).lower() for kw in quality_keywords) if pd.notna(x) else False
        )
        quality_events = events_df[mask]
    else:
        return {"quality_downtime_min": 0, "quality_event_count": 0}

    return {
        "quality_downtime_min": float(quality_events["downtime_min"].sum()),
        "quality_event_count": len(quality_events),
    }


def quality_issue_pareto(events_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """质量异常 Pareto。"""
    if "raw_reason" not in events_df.columns:
        return pd.DataFrame()

    # 筛选质量相关事件
    quality_keywords = ["quality", "defect", "scrap", "rework", "aoi", "inspection", "质量", "虚焊", "桥连"]
    mask = events_df["raw_reason"].str.lower().apply(
        lambda x: any(kw in str(x).lower() for kw in quality_keywords) if pd.notna(x) else False
    )
    quality_events = events_df[mask]

    if quality_events.empty:
        return pd.DataFrame()

    grouped = quality_events.groupby("raw_reason").agg(
        total_downtime_min=("downtime_min", "sum"),
        event_count=("event_id", "count"),
    ).reset_index()

    grouped.columns = ["issue", "impact_min", "count"]
    grouped = grouped.sort_values("impact_min", ascending=False).head(top_n)

    total = grouped["impact_min"].sum()
    grouped["ratio"] = (grouped["impact_min"] / total).round(4) if total > 0 else 0

    return grouped


def quality_issue_recurrence(events_df: pd.DataFrame) -> list[dict]:
    """统计质量异常复发情况。"""
    if "raw_reason" not in events_df.columns:
        return []

    grouped = events_df.groupby("raw_reason").agg(
        count=("event_id", "count"),
        total_downtime_min=("downtime_min", "sum"),
    ).reset_index()

    # 只返回发生 2 次以上的
    repeated = grouped[grouped["count"] >= 2].sort_values("count", ascending=False)

    result = []
    for _, row in repeated.iterrows():
        result.append({
            "issue": row["raw_reason"],
            "count": int(row["count"]),
            "total_downtime_min": float(row["total_downtime_min"]),
        })

    return result
