"""列映射 + 数据清洗测试。"""

import pytest
import pandas as pd

from src.adapters.data_cleaner import clean_dataframe, _normalize_nulls, _coerce_numeric
from src.adapters.column_mapper import MappingSuggestion, ColumnMapping


class TestNormalizeNulls:
    def test_na_values(self):
        s = pd.Series(["48", "N/A", "25", "-", "80"])
        cleaned, count = _normalize_nulls(s)
        assert count == 2  # N/A 和 -
        assert pd.isna(cleaned.iloc[1])
        assert pd.isna(cleaned.iloc[3])

    def test_chinese_nulls(self):
        s = pd.Series(["设备故障", "无", "换线", "未知"])
        cleaned, count = _normalize_nulls(s)
        assert count == 2

    def test_clean_values_preserved(self):
        s = pd.Series(["48", "25", "80"])
        cleaned, count = _normalize_nulls(s)
        assert count == 0
        assert list(cleaned) == ["48", "25", "80"]


class TestCoerceNumeric:
    def test_pure_numbers(self):
        s = pd.Series(["48", "25", "80"])
        result = _coerce_numeric(s)
        assert list(result) == [48.0, 25.0, 80.0]

    def test_comma_numbers(self):
        s = pd.Series(["1,500", "2,300"])
        result = _coerce_numeric(s)
        assert list(result) == [1500.0, 2300.0]

    def test_with_units(self):
        s = pd.Series(["48 min", "25 分钟"])
        result = _coerce_numeric(s)
        assert list(result) == [48.0, 25.0]

    def test_dirty_values_to_null(self):
        s = pd.Series(["48", "N/A", "-", "无"])
        result = _coerce_numeric(s)
        assert result.iloc[0] == 48.0
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])
        assert pd.isna(result.iloc[3])


class TestCleanDataframe:
    def test_basic_clean(self):
        df = pd.DataFrame({
            "Machine": ["MX-1001", "MX-2002", "MX-3006"],
            "Downtime": ["48", "N/A", "80"],
            "Reason": ["故障", "换线", "卡料"],
        })
        mappings = {"downtime_min": "Downtime", "raw_reason": "Reason", "machine_id": "Machine"}
        cleaned, report = clean_dataframe(df, mappings)

        assert report.rows_before == 3
        assert report.rows_after == 3
        assert len(report.column_cleanups) == 3
        assert "downtime_min" in cleaned.columns

    def test_deduplication(self):
        df = pd.DataFrame({
            "Downtime": ["48", "48", "80"],
            "Reason": ["故障", "故障", "卡料"],
        })
        mappings = {"downtime_min": "Downtime", "raw_reason": "Reason"}
        cleaned, report = clean_dataframe(df, mappings, deduplicate=True)
        assert report.duplicates_removed == 1
        assert report.rows_after == 2

    def test_column_rename(self):
        df = pd.DataFrame({"停机时长": ["48", "25"], "故障描述": ["A", "B"]})
        mappings = {"downtime_min": "停机时长", "raw_reason": "故障描述"}
        cleaned, report = clean_dataframe(df, mappings)
        assert "downtime_min" in cleaned.columns
        assert "raw_reason" in cleaned.columns
        assert "停机时长" not in cleaned.columns


class TestMappingSuggestion:
    def test_to_adapter_mapping(self):
        ms = MappingSuggestion(
            mappings=[
                ColumnMapping("停机时长", "downtime_min", 0.95),
                ColumnMapping("故障描述", "raw_reason", 0.90),
                ColumnMapping("col_7", None, 0.0),
            ],
            unmapped_columns=["col_7"],
        )
        adapter_map = ms.to_adapter_mapping()
        assert adapter_map == {"downtime_min": "停机时长", "raw_reason": "故障描述"}
