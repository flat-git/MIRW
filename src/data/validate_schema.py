"""数据 schema 校验函数。"""

from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """校验结果。"""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def validate_production_runs(df: pd.DataFrame) -> ValidationResult:
    """校验 production_run DataFrame。"""
    errors: list[str] = []
    warnings: list[str] = []

    # 必需字段
    required_cols = ["run_id", "source_dataset"]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"缺少必需字段: {col}")

    if errors:
        return ValidationResult(passed=False, errors=errors)

    # run_id 唯一性
    if df["run_id"].duplicated().any():
        dup_count = df["run_id"].duplicated().sum()
        errors.append(f"run_id 存在 {dup_count} 条重复记录")

    # source_dataset 非空
    if df["source_dataset"].isna().any() or (df["source_dataset"] == "").any():
        errors.append("source_dataset 存在空值")

    # 时间字段顺序校验
    if "planned_start" in df.columns and "planned_end" in df.columns:
        mask = df["planned_start"].notna() & df["planned_end"].notna()
        invalid = df.loc[mask & (df["planned_end"] < df["planned_start"])]
        if len(invalid) > 0:
            errors.append(f"存在 {len(invalid)} 条记录 planned_end < planned_start")

    if "actual_start" in df.columns and "actual_end" in df.columns:
        mask = df["actual_start"].notna() & df["actual_end"].notna()
        invalid = df.loc[mask & (df["actual_end"] < df["actual_start"])]
        if len(invalid) > 0:
            errors.append(f"存在 {len(invalid)} 条记录 actual_end < actual_start")

    # 非负字段
    for col in ["planned_time_min", "runtime_min", "downtime_min"]:
        if col in df.columns:
            neg = df[col].dropna()
            neg = neg[neg < 0]
            if len(neg) > 0:
                errors.append(f"{col} 存在 {len(neg)} 条负值记录")

    stats = {
        "total_runs": len(df),
        "duplicate_run_ids": int(df["run_id"].duplicated().sum()),
    }

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, stats=stats)


def validate_downtime_events(df: pd.DataFrame) -> ValidationResult:
    """校验 downtime_event DataFrame。"""
    errors: list[str] = []
    warnings: list[str] = []

    # 必需字段
    required_cols = ["event_id", "source_dataset", "downtime_min", "raw_reason"]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"缺少必需字段: {col}")

    if errors:
        return ValidationResult(passed=False, errors=errors)

    # event_id 唯一性
    if df["event_id"].duplicated().any():
        dup_count = df["event_id"].duplicated().sum()
        errors.append(f"event_id 存在 {dup_count} 条重复记录")

    # downtime_min 非负
    neg = df["downtime_min"].dropna()
    neg = neg[neg < 0]
    if len(neg) > 0:
        errors.append(f"downtime_min 存在 {len(neg)} 条负值记录")

    # raw_reason 非空
    if df["raw_reason"].isna().any() or (df["raw_reason"] == "").any():
        errors.append("raw_reason 存在空值")

    # source_dataset 非空
    if df["source_dataset"].isna().any() or (df["source_dataset"] == "").any():
        errors.append("source_dataset 存在空值")

    # 时间顺序
    if "event_start" in df.columns and "event_end" in df.columns:
        mask = df["event_start"].notna() & df["event_end"].notna()
        invalid = df.loc[mask & (df["event_end"] < df["event_start"])]
        if len(invalid) > 0:
            errors.append(f"存在 {len(invalid)} 条记录 event_end < event_start")

    stats = {
        "total_events": len(df),
        "duplicate_event_ids": int(df["event_id"].duplicated().sum()),
        "null_downtime": int(df["downtime_min"].isna().sum()),
        "null_raw_reason": int(df["raw_reason"].isna().sum()),
    }

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, stats=stats)


def validate_issue_reviews(df: pd.DataFrame) -> ValidationResult:
    """校验 issue_review DataFrame。"""
    errors: list[str] = []
    warnings: list[str] = []

    required_cols = ["issue_id", "issue_summary", "issue_type"]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"缺少必需字段: {col}")

    if errors:
        return ValidationResult(passed=False, errors=errors)

    if df["issue_id"].duplicated().any():
        dup_count = df["issue_id"].duplicated().sum()
        errors.append(f"issue_id 存在 {dup_count} 条重复记录")

    stats = {
        "total_issues": len(df),
        "duplicate_issue_ids": int(df["issue_id"].duplicated().sum()),
    }

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, stats=stats)
