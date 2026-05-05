"""Capability-aware OEE 计算。

缺字段时不伪造，只输出可计算的部分。
"""

from __future__ import annotations

import pandas as pd


def calculate_oee(runs_df: pd.DataFrame) -> list[dict]:
    """计算每条 production_run 的 OEE 指标。

    OEE = Availability × Performance × Quality
    Availability = Runtime / Planned Production Time
    Performance = Ideal Cycle Time × Total Count / Runtime
    Quality = Good Count / Total Count
    """
    results = []

    for _, row in runs_df.iterrows():
        result = _calculate_single_oee(row)
        results.append(result)

    return results


def calculate_aggregate_oee(runs_df: pd.DataFrame) -> dict:
    """计算聚合 OEE 指标（所有 run 汇总）。"""
    total_planned = 0.0
    total_runtime = 0.0
    total_count = 0.0
    good_count = 0.0

    has_planned = "planned_time_min" in runs_df.columns
    has_runtime = "runtime_min" in runs_df.columns
    has_actual = "actual_output" in runs_df.columns
    has_good = "good_output" in runs_df.columns

    if has_planned:
        total_planned = runs_df["planned_time_min"].sum()
    if has_runtime:
        total_runtime = runs_df["runtime_min"].sum()
    if has_actual:
        total_count = runs_df["actual_output"].sum()
    if has_good:
        good_count = runs_df["good_output"].sum()

    availability = None
    if has_planned and has_runtime and total_planned > 0:
        availability = total_runtime / total_planned

    quality = None
    if has_good and has_actual and total_count > 0:
        quality = good_count / total_count

    # Performance 需要 ideal_cycle_time，聚合时不计算
    performance = None
    oee = None

    capability = {
        "full_oee": False,
        "missing_fields": [],
    }

    if availability is not None and performance is not None and quality is not None:
        capability["full_oee"] = True
        oee = availability * performance * quality
    else:
        if availability is None:
            capability["missing_fields"].append("planned_time_min or runtime_min")
        if performance is None:
            capability["missing_fields"].append("ideal_cycle_time")
        if quality is None:
            capability["missing_fields"].append("good_output or actual_output")

    return {
        "availability": round(availability, 4) if availability is not None else None,
        "performance": round(performance, 4) if performance is not None else None,
        "quality": round(quality, 4) if quality is not None else None,
        "oee": round(oee, 4) if oee is not None else None,
        "capability": capability,
        "totals": {
            "planned_time_min": total_planned,
            "runtime_min": total_runtime,
            "total_count": total_count,
            "good_count": good_count,
        },
    }


def _calculate_single_oee(row: pd.Series) -> dict:
    """计算单条 run 的 OEE。"""
    planned = row.get("planned_time_min")
    runtime = row.get("runtime_min")
    actual = row.get("actual_output")
    good = row.get("good_output")
    ideal_ct = row.get("ideal_cycle_time")

    availability = None
    performance = None
    quality = None
    oee = None

    if pd.notna(planned) and pd.notna(runtime) and planned > 0:
        availability = runtime / planned

    if pd.notna(ideal_ct) and pd.notna(actual) and pd.notna(runtime) and runtime > 0:
        performance = (ideal_ct * actual) / runtime

    if pd.notna(good) and pd.notna(actual) and actual > 0:
        quality = good / actual

    if all(x is not None for x in [availability, performance, quality]):
        oee = availability * performance * quality

    missing = []
    if availability is None:
        missing.append("planned_time_min or runtime_min")
    if performance is None:
        missing.append("ideal_cycle_time")
    if quality is None:
        missing.append("good_output or actual_output")

    return {
        "run_id": row.get("run_id"),
        "availability": round(availability, 4) if availability is not None else None,
        "performance": round(performance, 4) if performance is not None else None,
        "quality": round(quality, 4) if quality is not None else None,
        "oee": round(oee, 4) if oee is not None else None,
        "capability": {
            "full_oee": oee is not None,
            "missing_fields": missing,
        },
    }
