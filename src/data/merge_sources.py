"""多数据源合并。"""

from __future__ import annotations

import pandas as pd


def merge_production_runs(*dataframes: pd.DataFrame) -> pd.DataFrame:
    """合并多个数据源的 production_run 表。"""
    non_empty = [df for df in dataframes if df is not None and len(df) > 0]
    if not non_empty:
        return pd.DataFrame()
    return pd.concat(non_empty, ignore_index=True)


def merge_downtime_events(*dataframes: pd.DataFrame) -> pd.DataFrame:
    """合并多个数据源的 downtime_event 表。"""
    non_empty = [df for df in dataframes if df is not None and len(df) > 0]
    if not non_empty:
        return pd.DataFrame()
    merged = pd.concat(non_empty, ignore_index=True)

    # 确保 event_id 唯一（加上 source_dataset 前缀）
    if "source_dataset" in merged.columns and "event_id" in merged.columns:
        merged["event_id"] = merged.apply(
            lambda r: f"{r['source_dataset']}_{r['event_id']}"
            if not str(r["event_id"]).startswith(r["source_dataset"])
            else r["event_id"],
            axis=1,
        )

    return merged
