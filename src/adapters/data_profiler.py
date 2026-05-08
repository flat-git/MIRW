"""数据文件画像分析（纯 Python，无 LLM）。

读取 CSV/Excel 的列名、样例值、类型、脏值检测，供后续 LLM 列映射使用。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pandas as pd


# 脏值正则模式
DIRTY_NULL_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^(N/A|NA|na|n/a|NaN|nan)$"),
    re.compile(r"^(-|—|--|---|——)$"),
    re.compile(r"^(无|未知|TBD|tbd|TBA|待定|待确认|没有|不清楚)$"),
    re.compile(r"^(null|NULL|Null|none|None|NONE)$"),
    re.compile(r"^(missing|Missing|MISSING|\\N)$"),
]

SAMPLE_ROWS = 5  # 读取的样例行数


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_count: int = 0
    null_ratio: float = 0.0
    unique_count: int = 0
    sample_values: list[str] = field(default_factory=list)
    is_numeric: bool = False
    is_datetime: bool = False
    detected_issues: list[str] = field(default_factory=list)


@dataclass
class SheetProfile:
    name: str
    total_rows: int = 0
    columns: list[ColumnProfile] = field(default_factory=list)


@dataclass
class FileProfile:
    file_name: str = ""
    file_path: str = ""
    total_rows: int = 0
    sheets: list[SheetProfile] = field(default_factory=list)
    encoding: str = "utf-8"

    def to_dict(self) -> dict:
        return asdict(self)


def profile_file(file_path: str | Path, sample_rows: int = SAMPLE_ROWS) -> FileProfile:
    """分析文件结构，返回列画像。"""
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return _profile_excel(file_path, sample_rows)
    elif suffix == ".csv":
        return _profile_csv(file_path, sample_rows)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")


def _profile_csv(file_path: Path, sample_rows: int) -> FileProfile:
    """分析 CSV 文件。"""
    encoding = _detect_encoding(file_path)
    df = pd.read_csv(file_path, nrows=sample_rows, dtype=str, encoding=encoding)
    df_full = pd.read_csv(file_path, dtype=str, encoding=encoding)

    columns = [_profile_column(df_full, col) for col in df_full.columns]
    sheet = SheetProfile(
        name="Sheet1",
        total_rows=len(df_full),
        columns=columns,
    )

    return FileProfile(
        file_name=file_path.name,
        file_path=str(file_path),
        total_rows=len(df_full),
        sheets=[sheet],
        encoding=encoding,
    )


def _profile_excel(file_path: Path, sample_rows: int) -> FileProfile:
    """分析 Excel 文件（多 sheet）。"""
    xls = pd.ExcelFile(file_path)
    sheets = []

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
        if df.empty:
            continue
        columns = [_profile_column(df, col) for col in df.columns]
        sheets.append(SheetProfile(
            name=sheet_name,
            total_rows=len(df),
            columns=columns,
        ))

    return FileProfile(
        file_name=file_path.name,
        file_path=str(file_path),
        total_rows=sum(s.total_rows for s in sheets),
        sheets=sheets,
        encoding="excel",
    )


def _profile_column(df: pd.DataFrame, col_name: str) -> ColumnProfile:
    """分析单列。"""
    series = df[col_name]
    total = len(series)
    null_count = int(series.isna().sum())

    # 统计 "文本 null"（字符串形式的脏值）
    text_null_count = sum(
        1 for v in series.dropna()
        if _is_dirty_null(str(v))
    )
    effective_null = null_count + text_null_count

    # 取非空、非脏值的样例
    clean_values = [
        str(v) for v in series.dropna()
        if not _is_dirty_null(str(v))
    ]
    sample_values = clean_values[:5]

    unique_count = len(set(clean_values))

    # 类型探测
    is_numeric = _can_be_numeric(clean_values)
    is_datetime = _can_be_datetime(clean_values)

    # 问题检测
    issues = []
    if text_null_count > 0:
        dirty_samples = [
            str(v) for v in series.dropna()
            if _is_dirty_null(str(v))
        ][:3]
        issues.append(f"含脏值({text_null_count}个): {', '.join(dirty_samples)}")

    if is_numeric:
        comma_values = [v for v in clean_values if "," in v and re.match(r"^[\d,]+\.?\d*$", v)]
        if comma_values:
            issues.append(f"千分位逗号: {comma_values[0]}")
        unit_values = [v for v in clean_values if re.search(r"\d+\s*(min|分钟|小时|h|hrs)", v, re.IGNORECASE)]
        if unit_values:
            issues.append(f"含单位后缀: {unit_values[0]}")

    if effective_null / total > 0.5 if total > 0 else False:
        issues.append(f"空值率过高: {effective_null/total:.0%}")

    return ColumnProfile(
        name=str(col_name),
        dtype=str(series.dtype),
        null_count=effective_null,
        null_ratio=round(effective_null / total, 3) if total > 0 else 0,
        unique_count=unique_count,
        sample_values=sample_values,
        is_numeric=is_numeric,
        is_datetime=is_datetime,
        detected_issues=issues,
    )


def _is_dirty_null(value: str) -> bool:
    """检测字符串是否为脏值 null。"""
    for pattern in DIRTY_NULL_PATTERNS:
        if pattern.match(value):
            return True
    return False


def _can_be_numeric(values: list[str]) -> bool:
    """检测值列表能否转为数值。"""
    if not values:
        return False
    tested = 0
    convertible = 0
    for v in values[:20]:
        tested += 1
        cleaned = v.replace(",", "").strip()
        # 去掉单位后缀
        cleaned = re.sub(r"\s*(min|分钟|小时|h|hrs|pcs|units?)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
        try:
            float(cleaned)
            convertible += 1
        except ValueError:
            pass
    return convertible / tested > 0.5 if tested > 0 else False


def _can_be_datetime(values: list[str]) -> bool:
    """检测值列表能否转为日期。"""
    if not values:
        return False
    tested = 0
    convertible = 0
    for v in values[:10]:
        tested += 1
        try:
            pd.to_datetime(v)
            convertible += 1
        except (ValueError, TypeError):
            pass
    return convertible / tested > 0.5 if tested > 0 else False


def _detect_encoding(file_path: Path) -> str:
    """尝试检测文件编码。"""
    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read(10000)
        result = chardet.detect(raw)
        return result.get("encoding", "utf-8") or "utf-8"
    except ImportError:
        # chardet 未安装，尝试常见编码
        for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    f.read(1000)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return "utf-8"
