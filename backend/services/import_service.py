"""导入编排服务：profile → map → clean → validate → store。"""

from __future__ import annotations

import sys
import uuid
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.state import store
from backend.services.dataset_service import _build_summary, _convert_numpy, _build_pipeline
from src.adapters.data_profiler import profile_file
from src.adapters.column_mapper import suggest_mapping
from src.adapters.data_cleaner import clean_dataframe
from src.adapters.generic_excel_adapter import GenericExcelAdapter
from src.data.validate_schema import validate_production_runs, validate_downtime_events


# 临时缓存：analysis_id → {file_path, profile, suggestion}
_analysis_cache: dict[str, dict] = {}


def analyze_file(file_path: str | Path) -> dict:
    """Step 1: 分析文件结构 + LLM 列映射建议。"""
    file_path = Path(file_path)
    analysis_id = uuid.uuid4().hex[:8]

    # 1. Profile
    profile = profile_file(file_path)

    # 2. LLM mapping
    suggestion = suggest_mapping(profile)

    # 3. 缓存
    _analysis_cache[analysis_id] = {
        "file_path": str(file_path),
        "profile": profile,
        "suggestion": suggestion,
    }

    # 4. 检测结构
    first_sheet = profile.sheets[0] if profile.sheets else None
    col_names = [c.name for c in first_sheet.columns] if first_sheet else []
    has_event_fields = any(
        _has_keyword(c, ["event", "downtime", "reason", "cause"])
        for c in col_names
    )
    structure = "event_level" if has_event_fields else "aggregated"

    return {
        "analysis_id": analysis_id,
        "file_name": profile.file_name,
        "total_rows": profile.total_rows,
        "columns": [c.__dict__ for c in (first_sheet.columns if first_sheet else [])],
        "suggested_mappings": [m.__dict__ for m in suggestion.mappings],
        "unmapped_columns": suggestion.unmapped_columns,
        "detected_structure": structure,
    }


def execute_import(analysis_id: str, confirmed_mappings: list[dict],
                   deduplicate: bool = True, normalize_nulls: bool = True,
                   coerce_types: bool = True) -> dict:
    """Step 2: 用户确认映射后执行导入。"""
    cache = _analysis_cache.get(analysis_id)
    if cache is None:
        raise ValueError(f"分析 ID {analysis_id} 不存在或已过期，请重新上传文件")

    file_path = cache["file_path"]

    # 构造映射 {target_field: source_column}
    mappings = {}
    for m in confirmed_mappings:
        target = m.get("target_field")
        source = m.get("source_column")
        if target and source:
            mappings[target] = source

    # 读取原始数据
    file_suffix = Path(file_path).suffix.lower()
    if file_suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, dtype=str)
    else:
        df = pd.read_csv(file_path, dtype=str)

    # 清洗
    cleaned_df, cleaning_report = clean_dataframe(
        df, mappings,
        deduplicate=deduplicate,
        normalize_nulls=normalize_nulls,
        coerce_types=coerce_types,
    )

    # 用 GenericExcelAdapter 的逻辑构造 production_runs 和 downtime_events
    # 但直接用映射后的 DataFrame，不走 YAML
    dataset_id = f"upload_{store.generate_id()}"
    runs_df, events_df = _split_into_canonical(cleaned_df, mappings)

    # 校验
    runs_val = validate_production_runs(runs_df) if len(runs_df) > 0 else type("V", (), {"passed": True, "errors": [], "stats": {}})()
    events_val = validate_downtime_events(events_df) if len(events_df) > 0 else type("V", (), {"passed": True, "errors": [], "stats": {}})()

    # Capability（直接检测，不走 BaseAdapter）
    capability = _detect_capability(runs_df, events_df)

    validation = {
        "production_runs": {"passed": runs_val.passed, "errors": runs_val.errors, "stats": runs_val.stats},
        "downtime_events": {"passed": events_val.passed, "errors": events_val.errors, "stats": events_val.stats},
        "capability": _convert_numpy(capability),
    }

    pipeline = _build_pipeline(runs_df, events_df, validation, None)
    store.store(dataset_id, runs_df, events_df, validation, "upload", pipeline, None)

    # 清理缓存
    del _analysis_cache[analysis_id]

    summary = _build_summary(dataset_id)
    summary["cleaning_report"] = cleaning_report.to_dict()
    return summary


def _split_into_canonical(df: pd.DataFrame, mappings: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """将清洗后的 DataFrame 拆分为 production_runs 和 downtime_events。"""
    # 重命名
    reverse_map = {v: k for k, v in mappings.items() if v in df.columns}
    renamed = df.rename(columns=reverse_map)

    source_name = "upload"

    # Downtime Events
    event_cols = ["downtime_min", "raw_reason", "raw_note", "machine_id",
                  "operator_id", "shift", "product_id", "line_id",
                  "event_start", "event_end"]
    available_event_cols = [c for c in event_cols if c in renamed.columns]

    if available_event_cols:
        events_df = renamed[available_event_cols].copy()
        events_df["source_dataset"] = source_name
        if "event_id" not in events_df.columns:
            events_df["event_id"] = [f"{source_name}_E{i+1:04d}" for i in range(len(events_df))]
        if "downtime_min" in events_df.columns:
            events_df["downtime_min"] = pd.to_numeric(events_df["downtime_min"], errors="coerce").fillna(0.0)
        if "raw_reason" not in events_df.columns:
            events_df["raw_reason"] = "Unknown"
    else:
        events_df = pd.DataFrame()

    # Production Runs（按行生成，或聚合）
    run_cols = ["run_id", "line_id", "product_id", "operator_id", "shift",
                "planned_time_min", "runtime_min", "downtime_min",
                "target_output", "actual_output", "good_output", "scrap_output"]
    available_run_cols = [c for c in run_cols if c in renamed.columns]

    if available_run_cols:
        runs_df = renamed[available_run_cols].copy()
        runs_df["source_dataset"] = source_name
        if "run_id" not in runs_df.columns:
            runs_df["run_id"] = [f"{source_name}_RUN_{i+1:04d}" for i in range(len(runs_df))]
        # 转数值列
        for num_col in ["planned_time_min", "runtime_min", "downtime_min",
                        "target_output", "actual_output", "good_output", "scrap_output"]:
            if num_col in runs_df.columns:
                runs_df[num_col] = pd.to_numeric(runs_df[num_col], errors="coerce")
    else:
        runs_df = pd.DataFrame()

    return runs_df, events_df


def _has_keyword(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _detect_capability(runs_df: pd.DataFrame, events_df: pd.DataFrame) -> dict:
    """直接检测能力（不依赖 BaseAdapter 抽象类）。"""
    has_events = len(events_df) > 0
    has_runs = len(runs_df) > 0
    return {
        "downtime_pareto": has_events and "downtime_min" in events_df.columns and "raw_reason" in events_df.columns,
        "ie_loss_review": has_events and "downtime_min" in events_df.columns,
        "repeated_issue_retrieval": has_events and "raw_note" in events_df.columns and events_df["raw_note"].notna().any(),
        "full_oee": has_runs and all(c in runs_df.columns for c in ["planned_time_min", "runtime_min", "actual_output", "good_output"]),
        "availability_only": has_runs and all(c in runs_df.columns for c in ["planned_time_min", "runtime_min"]),
        "quality_rate": has_runs and "good_output" in runs_df.columns and "actual_output" in runs_df.columns,
        "scrap_rate": has_runs and "scrap_output" in runs_df.columns,
        "shift_analysis": has_events and "shift" in events_df.columns,
        "operator_analysis": has_events and "operator_id" in events_df.columns,
        "product_analysis": has_events and "product_id" in events_df.columns,
        "machine_analysis": has_events and "machine_id" in events_df.columns,
        "location_analysis": has_events and "line_id" in events_df.columns,
        "missing_fields": [],
    }
