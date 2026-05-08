"""数据画像分析测试。"""

import os
import pytest
import pandas as pd
from pathlib import Path

from src.adapters.data_profiler import profile_file, _is_dirty_null, _can_be_numeric, ColumnProfile


TEST_DIR = Path(__file__).resolve().parent.parent / "data" / "test_dirty"


class TestDirtyNull:
    def test_na_patterns(self):
        for v in ["N/A", "NA", "n/a", "NaN", "nan"]:
            assert _is_dirty_null(v), f"Should detect '{v}' as dirty null"

    def test_dash_patterns(self):
        for v in ["-", "—", "--", "---"]:
            assert _is_dirty_null(v), f"Should detect '{v}' as dirty null"

    def test_chinese_patterns(self):
        for v in ["无", "未知", "待定", "TBD", "null", "NULL", "none"]:
            assert _is_dirty_null(v), f"Should detect '{v}' as dirty null"

    def test_clean_values(self):
        for v in ["设备故障", "48", "OK", "正常", "MX-1001"]:
            assert not _is_dirty_null(v), f"'{v}' should NOT be dirty null"

    def test_empty_or_whitespace(self):
        assert _is_dirty_null("")
        assert _is_dirty_null("  ")
        assert _is_dirty_null("\t")


class TestCanBeNumeric:
    def test_pure_numbers(self):
        assert _can_be_numeric(["48", "25", "80", "110"]) is True

    def test_with_commas(self):
        assert _can_be_numeric(["1,500", "2,300", "48"]) is True

    def test_with_units(self):
        assert _can_be_numeric(["48 min", "25 分钟", "80 min"]) is True

    def test_text_values(self):
        assert _can_be_numeric(["设备故障", "换线", "卡料"]) is False

    def test_mixed(self):
        assert _can_be_numeric(["48", "N/A", "25", "-", "80"]) is True


class TestProfileFile:
    @pytest.mark.skipif(not (TEST_DIR / "dirty_chinese_columns.csv").exists(), reason="测试文件不存在")
    def test_chinese_columns(self):
        profile = profile_file(TEST_DIR / "dirty_chinese_columns.csv")
        assert profile.total_rows == 5
        assert len(profile.sheets) == 1
        sheet = profile.sheets[0]
        assert len(sheet.columns) == 7
        col_names = [c.name for c in sheet.columns]
        assert "设备编号" in col_names
        assert "停机时长(分钟)" in col_names

    @pytest.mark.skipif(not (TEST_DIR / "dirty_messy_values.csv").exists(), reason="测试文件不存在")
    def test_messy_values_detection(self):
        profile = profile_file(TEST_DIR / "dirty_messy_values.csv")
        sheet = profile.sheets[0]

        # 找 Downtime 列
        dt_col = next(c for c in sheet.columns if c.name == "Downtime")
        # 应检测到脏值 (N/A, -, 1500 with comma, "80 min" with unit, "无")
        assert dt_col.null_count > 0
        assert len(dt_col.detected_issues) > 0
        issues_text = " ".join(dt_col.detected_issues)
        assert "脏值" in issues_text or "千分位" in issues_text or "单位" in issues_text

    @pytest.mark.skipif(not (TEST_DIR / "dirty_messy_values.csv").exists(), reason="测试文件不存在")
    def test_numeric_detection(self):
        profile = profile_file(TEST_DIR / "dirty_messy_values.csv")
        sheet = profile.sheets[0]
        dt_col = next(c for c in sheet.columns if c.name == "Downtime")
        # Downtime 列虽然有脏值，但大部分是数值，应识别为 numeric
        assert dt_col.is_numeric is True

    def test_to_dict(self):
        profile = profile_file(TEST_DIR / "dirty_chinese_columns.csv")
        d = profile.to_dict()
        assert "file_name" in d
        assert "sheets" in d
        assert len(d["sheets"]) > 0
