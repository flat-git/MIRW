"""数据源加载服务。调用 src/adapters 加载数据。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

# 确保 src 在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.state import store
from src.adapters.maven_downtime_adapter import MavenDowntimeAdapter
from src.adapters.gomask_downtime_adapter import GoMaskDowntimeAdapter
from src.adapters.kaggle_oee_adapter import KaggleOEEAdapter
from src.adapters.generic_excel_adapter import GenericExcelAdapter
from src.data.sample_data import load_synthetic_notes
from src.data.sample_data import load_synthetic_action_items
from src.data.sample_data import load_generic_excel_mapping
from src.config.settings import settings
from src.metrics.efficiency import calculate_efficiency_summary
from src.metrics.pareto import top_loss_pareto
from src.metrics.downtime import (
    downtime_by_category, downtime_by_product,
    downtime_by_operator, downtime_by_machine,
)


ADAPTER_MAP = {
    "maven": lambda: MavenDowntimeAdapter(),
    "gomask": lambda: GoMaskDowntimeAdapter(),
    "kaggle": lambda: KaggleOEEAdapter(),
}

DATA_PATH_MAP = {
    "maven": settings.data_dir / "raw" / "maven",
    "gomask": settings.data_dir / "raw" / "gomask",
    "kaggle": settings.data_dir / "raw" / "kaggle_oee",
}


def load_dataset(source: str) -> dict:
    """加载数据源，返回数据集摘要。"""
    dataset_id = f"{source}_{store.generate_id()}"

    if source == "synthetic":
        notes_df = load_synthetic_notes()
        actions_df = load_synthetic_action_items()
        validation = {
            "production_runs": {"passed": True, "errors": [], "stats": {"row_count": 0}},
            "downtime_events": {"passed": True, "errors": [], "stats": {"row_count": len(notes_df)}},
            "capability": _detect_basic_capability(pd.DataFrame(), notes_df),
        }
        pipeline = _build_pipeline(pd.DataFrame(), notes_df, validation, actions_df)
        store.store(dataset_id, pd.DataFrame(), notes_df, validation, source, pipeline, actions_df)
        return _build_summary(dataset_id)

    if source not in ADAPTER_MAP:
        raise ValueError(f"不支持的数据源: {source}")

    adapter = ADAPTER_MAP[source]()
    data_path = DATA_PATH_MAP[source]
    raw = adapter.load_raw(data_path)
    runs_df = adapter.to_production_runs(raw)
    events_df = adapter.to_downtime_events(raw)
    validation = adapter.validate_output(runs_df, events_df)
    capability = adapter.detect_capability(runs_df, events_df)

    validation["capability"] = capability
    actions_df = _derive_actions(source, events_df)
    pipeline = _build_pipeline(runs_df, events_df, validation, actions_df)
    store.store(dataset_id, runs_df, events_df, validation, source, pipeline, actions_df)
    return _build_summary(dataset_id)


def upload_dataset(file_path: str | Path, mapping_text: str | None = None) -> dict:
    """加载用户上传的 Excel/CSV，返回数据集摘要。"""
    dataset_id = f"upload_{store.generate_id()}"

    if mapping_text and mapping_text.strip():
        mapping = yaml.safe_load(mapping_text)
    else:
        mapping = load_generic_excel_mapping()

    adapter = GenericExcelAdapter(mapping_dict=mapping)
    raw = adapter.load_raw(file_path)
    runs_df = adapter.to_production_runs(raw)
    events_df = adapter.to_downtime_events(raw)
    validation = adapter.validate_output(runs_df, events_df)
    validation["capability"] = adapter.detect_capability(runs_df, events_df)
    pipeline = _build_pipeline(runs_df, events_df, validation, None)
    store.store(dataset_id, runs_df, events_df, validation, "upload", pipeline, None)
    return _build_summary(dataset_id)


def get_dataset_summary(dataset_id: str) -> dict:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    return _build_summary(dataset_id)


def get_events(dataset_id: str, limit: int = 200) -> list[dict]:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    df = ds["events_df"].head(limit)
    return _df_to_records(df)


def get_runs(dataset_id: str, limit: int = 200) -> list[dict]:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    df = ds["runs_df"].head(limit)
    return _df_to_records(df)


def _build_summary(dataset_id: str) -> dict:
    ds = store.get(dataset_id)
    val = ds["validation"]
    pipeline = ds.get("pipeline", {})
    return {
        "dataset_id": dataset_id,
        "source": ds["source"],
        "run_count": ds["run_count"],
        "event_count": ds["event_count"],
        "loaded_at": ds["loaded_at"],
        "pipeline_status": pipeline.get("status", "completed"),
        "capability": _convert_numpy(val.get("capability", {})),
        "metrics_preview": _convert_numpy(pipeline.get("metrics_preview", {})),
        "cards": _convert_numpy(pipeline.get("cards", [])),
        "validation": {
            "production_runs": _convert_numpy(val.get("production_runs", {})),
            "downtime_events": _convert_numpy(val.get("downtime_events", {})),
        },
    }


def _build_pipeline(runs_df: pd.DataFrame, events_df: pd.DataFrame,
                    validation: dict, actions_df: pd.DataFrame | None) -> dict:
    """导入后同步计算轻量确定性结果，用于 dataset 总览。"""
    capability = validation.get("capability", {})
    efficiency = calculate_efficiency_summary(runs_df, events_df)
    pareto_df = top_loss_pareto(events_df, top_n=5)
    pareto = pareto_df.to_dict("records") if not pareto_df.empty else []

    group_counts = {
        "category": len(downtime_by_category(events_df)),
        "product": len(downtime_by_product(events_df)),
        "operator": len(downtime_by_operator(events_df)),
        "machine": len(downtime_by_machine(events_df)),
    }
    metrics_preview = {
        "efficiency": efficiency,
        "pareto": pareto,
        "groups": group_counts,
        "action_summary": _action_summary(actions_df),
    }
    return {
        "status": "completed",
        "metrics_preview": metrics_preview,
        "cards": _build_cards(capability, validation, events_df, metrics_preview),
    }


def _build_cards(capability: dict, validation: dict, events_df: pd.DataFrame,
                 metrics_preview: dict) -> list[dict]:
    events_ok = validation.get("downtime_events", {}).get("passed", False)
    runs_ok = validation.get("production_runs", {}).get("passed", False)
    has_raw_notes = (
        "raw_note" in events_df.columns
        and events_df["raw_note"].notna().any()
        and (events_df["raw_note"].fillna("") != "").any()
    )
    has_actions = metrics_preview.get("action_summary", {}).get("total", 0) > 0
    return [
        {
            "key": "validation",
            "title": "数据校验",
            "enabled": True,
            "reason": "查看导入记录、字段校验与能力检测",
            "route": "",
        },
        {
            "key": "loss",
            "title": "停机损失分析",
            "enabled": bool(capability.get("downtime_pareto") and events_ok),
            "reason": "需要 downtime_min 与 raw_reason 字段" if not capability.get("downtime_pareto") else "查看停机损失、效率与 Pareto",
            "route": "loss",
        },
        {
            "key": "events",
            "title": "事件明细",
            "enabled": len(events_df) > 0,
            "reason": "查看标准化后的 downtime events",
            "route": "events",
        },
        {
            "key": "similar",
            "title": "相似事件检索",
            "enabled": bool(has_raw_notes),
            "reason": "需要 raw_note 文本字段" if not has_raw_notes else "按异常描述检索历史相似事件",
            "route": "similar",
        },
        {
            "key": "reports",
            "title": "报告生成",
            "enabled": bool(capability.get("ie_loss_review") and events_ok),
            "reason": "需要有效停机事件" if not events_ok else "基于当前数据集生成 IE/CAPA 草稿",
            "route": "reports",
        },
        {
            "key": "actions",
            "title": "改善项跟踪",
            "enabled": bool(has_actions),
            "reason": "当前数据集没有改善项或 resolution_actions" if not has_actions else "查看当前数据集派生的改善项",
            "route": "actions",
        },
    ]


def _derive_actions(source: str, events_df: pd.DataFrame) -> pd.DataFrame | None:
    """从当前数据集派生只读改善项。"""
    if source == "gomask" and "metadata" in events_df.columns:
        rows = []
        for _, row in events_df.iterrows():
            meta = row.get("metadata") or {}
            action = meta.get("resolution_actions") if isinstance(meta, dict) else None
            if not action or pd.isna(action):
                continue
            rows.append({
                "action_id": f"A-{row.get('event_id')}",
                "related_event_id": row.get("event_id"),
                "problem": row.get("raw_note") or row.get("raw_reason") or "Downtime event",
                "temporary_action": action,
                "permanent_action": None,
                "owner": meta.get("resolved_by"),
                "due_date": None,
                "status": "Closed",
                "close_date": None,
                "recurrence_flag": False,
            })
        return pd.DataFrame(rows) if rows else None
    return None


def _action_summary(actions_df: pd.DataFrame | None) -> dict:
    if actions_df is None or actions_df.empty:
        return {"total": 0, "open": 0, "in_progress": 0, "closed": 0, "overdue": 0, "recurred": 0}
    status = actions_df.get("status", pd.Series(dtype=str)).fillna("")
    recurrence = actions_df.get("recurrence_flag", pd.Series(dtype=bool)).fillna(False)
    return {
        "total": len(actions_df),
        "open": int((status == "Open").sum()),
        "in_progress": int((status == "In Progress").sum()),
        "closed": int((status == "Closed").sum()),
        "overdue": 0,
        "recurred": int(recurrence.astype(bool).sum()),
    }


def _detect_basic_capability(runs_df: pd.DataFrame, events_df: pd.DataFrame) -> dict:
    return {
        "downtime_pareto": "downtime_min" in events_df.columns and "raw_reason" in events_df.columns,
        "ie_loss_review": "downtime_min" in events_df.columns,
        "repeated_issue_retrieval": "raw_note" in events_df.columns,
        "full_oee": False,
        "availability_only": False,
        "quality_rate": False,
        "scrap_rate": False,
        "shift_analysis": "shift" in events_df.columns,
        "operator_analysis": "operator_id" in events_df.columns,
        "product_analysis": "product_id" in events_df.columns,
        "missing_fields": ["planned_time_min", "runtime_min", "actual_output", "good_output", "ideal_cycle_time"],
    }


def _convert_numpy(obj):
    """递归将 numpy 类型转为 Python 原生类型，FastAPI 可序列化。"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → JSON-safe list。处理 NaN 和 datetime。"""
    import math
    from datetime import datetime as dt

    records = df.to_dict("records")
    cleaned = []
    for rec in records:
        clean = {}
        for k, v in rec.items():
            if v is None or (isinstance(v, float) and math.isnan(v)):
                clean[k] = None
            elif isinstance(v, (dt, pd.Timestamp)):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        cleaned.append(clean)
    return cleaned
