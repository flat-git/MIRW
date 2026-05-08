"""数据清洗引擎（纯 Python，无 LLM）。

处理脏值归一化、类型转换、去重等。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

import pandas as pd

from src.adapters.data_profiler import DIRTY_NULL_PATTERNS


@dataclass
class ColumnCleanup:
    column: str
    nulls_normalized: int = 0
    type_coerced: bool = False
    values_before: list[str] = field(default_factory=list)
    values_after: list[str] = field(default_factory=list)


@dataclass
class CleaningReport:
    rows_before: int = 0
    rows_after: int = 0
    duplicates_removed: int = 0
    column_cleanups: list[ColumnCleanup] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def clean_dataframe(
    df: pd.DataFrame,
    mappings: dict[str, str],
    deduplicate: bool = True,
    normalize_nulls: bool = True,
    coerce_types: bool = True,
) -> tuple[pd.DataFrame, CleaningReport]:
    """清洗 DataFrame。

    Args:
        df: 原始 DataFrame
        mappings: {target_field: source_column} 映射
        deduplicate: 是否去重
        normalize_nulls: 是否归一化脏值为 NaN
        coerce_types: 是否做类型转换

    Returns:
        (清洗后的 DataFrame, CleaningReport)
    """
    report = CleaningReport(rows_before=len(df))
    result = df.copy()

    # 只保留映射到的列 + 重命名
    col_map = {v: k for k, v in mappings.items() if v in result.columns}
    result = result.rename(columns=col_map)

    # 对每个映射到的列做清洗
    for target_col, source_col in mappings.items():
        if source_col not in df.columns:
            continue
        col_report = ColumnCleanup(column=source_col)

        if target_col in result.columns:
            series = result[target_col]

            # 脏值归一化
            if normalize_nulls:
                before_samples = series.dropna().astype(str).head(3).tolist()
                cleaned, n_normalized = _normalize_nulls(series)
                result[target_col] = cleaned
                after_samples = pd.Series(cleaned).dropna().astype(str).head(3).tolist()
                col_report.nulls_normalized = n_normalized
                col_report.values_before = before_samples
                col_report.values_after = after_samples

            # 类型转换
            if coerce_types:
                if target_col in ("downtime_min", "planned_time_min", "runtime_min",
                                  "target_output", "actual_output", "good_output", "scrap_output"):
                    result[target_col] = _coerce_numeric(result[target_col])
                    col_report.type_coerced = True
                elif target_col in ("event_start", "event_end", "planned_start", "planned_end"):
                    result[target_col] = _coerce_datetime(result[target_col])
                    col_report.type_coerced = True

        report.column_cleanups.append(col_report)

    # 去重
    if deduplicate:
        before_dedup = len(result)
        result = result.drop_duplicates()
        report.duplicates_removed = before_dedup - len(result)

    report.rows_after = len(result)
    return result, report


def _normalize_nulls(series: pd.Series) -> tuple[pd.Series, int]:
    """将脏值归一化为 NaN。"""
    result = series.copy()
    count = 0
    for i, val in result.items():
        if pd.isna(val):
            continue
        s = str(val).strip()
        if _is_dirty_value(s):
            result[i] = None
            count += 1
    return result, count


def _is_dirty_value(value: str) -> bool:
    """检测是否为脏值。"""
    for pattern in DIRTY_NULL_PATTERNS:
        if pattern.match(value):
            return True
    return False


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """将字符串列转为数值。处理千分位逗号和单位后缀。"""
    def convert(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        if _is_dirty_value(s):
            return None
        # 去掉千分位逗号
        s = s.replace(",", "")
        # 去掉单位后缀
        s = re.sub(r"\s*(min|分钟|小时|h|hrs|pcs|units?)\s*$", "", s, flags=re.IGNORECASE).strip()
        try:
            return float(s)
        except ValueError:
            return None

    return series.apply(convert)


def _coerce_datetime(series: pd.Series) -> pd.Series:
    """将字符串列转为日期。多格式尝试。"""
    def convert(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        if _is_dirty_value(s):
            return None
        try:
            return pd.to_datetime(s)
        except (ValueError, TypeError):
            return None

    return series.apply(convert)
