"""改善项服务。调用 src/actions 处理。"""

from __future__ import annotations

import pandas as pd

from backend.state import store


def get_action_items(dataset_id: str) -> list[dict]:
    df = _get_dataset_actions(dataset_id)
    if df is None or df.empty:
        return []
    records = df.to_dict("records")
    cleaned = []
    for rec in records:
        clean = {}
        for k, v in rec.items():
            if pd.isna(v):
                clean[k] = None
            else:
                clean[k] = v
        cleaned.append(clean)
    return cleaned


def get_action_summary(dataset_id: str) -> dict:
    df = _get_dataset_actions(dataset_id)
    if df is None or df.empty:
        return {
            "total": 0,
            "open": 0,
            "in_progress": 0,
            "closed": 0,
            "overdue": 0,
            "recurred": 0,
            "reason": "当前数据集没有改善项或 resolution_actions",
        }

    status_col = df.get("status", pd.Series(dtype=str)).fillna("")
    due = pd.to_datetime(df.get("due_date", pd.Series(dtype=str)), errors="coerce")
    closed = status_col == "Closed"
    overdue = (~closed) & due.notna() & (due < pd.Timestamp.today().normalize())
    recurrence = df.get("recurrence_flag", pd.Series(dtype=bool)).fillna(False).astype(bool)

    return {
        "total": len(df),
        "open": int((status_col == "Open").sum()),
        "in_progress": int((status_col == "In Progress").sum()),
        "closed": int(closed.sum()),
        "overdue": int(overdue.sum()),
        "recurred": int(recurrence.sum()),
        "reason": "",
    }


def _get_dataset_actions(dataset_id: str) -> pd.DataFrame | None:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    return ds.get("actions_df")
