"""Kaggle OEE 适配器测试。"""

import pytest
import pandas as pd

from src.adapters.kaggle_oee_adapter import KaggleOEEAdapter


@pytest.fixture
def sample_kaggle_data():
    """构造 Kaggle OEE 格式的测试数据。"""
    return {
        "main": pd.DataFrame({
            "Machine_ID": ["M01", "M02", "M01", "M02"],
            "Shift": ["Day", "Day", "Night", "Night"],
            "Downtime": [30, 45, 20, 35],
            "Downtime_Reason": ["Failure", "Setup", "Minor Stop", "Failure"],
            "Total_Count": [1000, 800, 1100, 850],
            "Good_Count": [980, 790, 1080, 830],
            "Defect_Count": [20, 10, 20, 20],
            "Planned_Production_Time": [480, 480, 480, 480],
            "Run_Time": [450, 435, 460, 445],
        })
    }


class TestKaggleOEEAdapter:
    def test_source_name(self):
        adapter = KaggleOEEAdapter()
        assert adapter.source_name == "kaggle_oee_downtime"

    def test_to_production_runs(self, sample_kaggle_data):
        adapter = KaggleOEEAdapter()
        runs = adapter.to_production_runs(sample_kaggle_data)

        assert len(runs) == 4
        assert "machine_id" in runs.columns
        assert "planned_time_min" in runs.columns
        assert "actual_output" in runs.columns

    def test_to_downtime_events(self, sample_kaggle_data):
        adapter = KaggleOEEAdapter()
        events = adapter.to_downtime_events(sample_kaggle_data)

        assert len(events) == 4
        assert "downtime_min" in events.columns
        assert all(events["downtime_min"] >= 0)

    def test_oee_capability(self, sample_kaggle_data):
        adapter = KaggleOEEAdapter()
        runs = adapter.to_production_runs(sample_kaggle_data)
        events = adapter.to_downtime_events(sample_kaggle_data)
        caps = adapter.detect_capability(runs, events)

        assert caps["downtime_pareto"] is True
        assert caps["quality_rate"] is True
        assert caps["scrap_rate"] is True
