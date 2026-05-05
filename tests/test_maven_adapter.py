"""Maven 适配器测试。适配真实 Excel 四表结构。"""

import pytest
import pandas as pd

from src.adapters.maven_downtime_adapter import MavenDowntimeAdapter


@pytest.fixture
def sample_maven_raw():
    """构造与真实 Maven Excel 一致的四表结构。"""
    line_productivity = pd.DataFrame({
        "Date": pd.to_datetime(["2024-08-29", "2024-08-29", "2024-08-30"]),
        "Product": ["OR-600", "LE-600", "CO-600"],
        "Batch": [422111, 422112, 422113],
        "Operator": ["Mac", "Mac", "Charlie"],
        "Start Time": ["11:50:00", "14:05:00", "08:00:00"],
        "End Time": ["14:05:00", "15:45:00", "10:30:00"],
    })

    products = pd.DataFrame({
        "Product": ["OR-600", "LE-600", "CO-600"],
        "Flavor": ["Orange", "Lemon lime", "Cola"],
        "Size": ["600 ml", "600 ml", "600 ml"],
        "Min batch time": [60, 60, 60],
    })

    downtime_factors = pd.DataFrame({
        "Factor": [1, 2, 3, 7],
        "Description": ["Emergency stop", "Batch change", "Labeling error", "Machine failure"],
        "Operator Error": ["No", "Yes", "No", "No"],
    })

    # Line downtime 宽表：首行是 header，之后是数据
    # 手动构造 DataFrame 模拟真实格式
    line_downtime = pd.DataFrame({
        "Unnamed: 0": ["Batch", 422111, 422112, 422113],
        "Downtime factor": [1.0, None, None, 15.0],
        "Unnamed: 2": [2.0, 60.0, 20.0, None],
        "Unnamed: 3": [3.0, None, None, None],
        "Unnamed: 4": [4.0, None, None, None],
        "Unnamed: 5": [5.0, None, None, None],
        "Unnamed: 6": [6.0, None, None, None],
        "Unnamed: 7": [7.0, 15.0, None, 30.0],
    })

    return {
        "Line productivity": line_productivity,
        "Products": products,
        "Downtime factors": downtime_factors,
        "Line downtime": line_downtime,
    }


class TestMavenDowntimeAdapter:
    def test_source_name(self):
        adapter = MavenDowntimeAdapter()
        assert adapter.source_name == "maven_manufacturing_downtime"

    def test_to_production_runs(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        runs = adapter.to_production_runs(sample_maven_raw)

        assert len(runs) == 3
        assert "run_id" in runs.columns
        assert "source_dataset" in runs.columns
        assert all(runs["source_dataset"] == "maven_manufacturing_downtime")

    def test_production_runs_have_product(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        runs = adapter.to_production_runs(sample_maven_raw)

        assert "product_id" in runs.columns
        assert set(runs["product_id"]) == {"OR-600", "LE-600", "CO-600"}

    def test_production_runs_runtime_positive(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        runs = adapter.to_production_runs(sample_maven_raw)

        assert all(runs["runtime_min"] > 0)

    def test_to_downtime_events(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        events = adapter.to_downtime_events(sample_maven_raw)

        assert len(events) > 0
        assert "event_id" in events.columns
        assert "downtime_min" in events.columns
        assert "raw_reason" in events.columns

    def test_event_id_unique(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        events = adapter.to_downtime_events(sample_maven_raw)
        assert events["event_id"].is_unique

    def test_downtime_non_negative(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        events = adapter.to_downtime_events(sample_maven_raw)
        assert all(events["downtime_min"] > 0)

    def test_downtime_events_have_reason(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        events = adapter.to_downtime_events(sample_maven_raw)
        assert all(events["raw_reason"].notna())
        assert all(events["raw_reason"] != "")

    def test_capability_detection(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        runs = adapter.to_production_runs(sample_maven_raw)
        events = adapter.to_downtime_events(sample_maven_raw)
        caps = adapter.detect_capability(runs, events)

        assert caps["downtime_pareto"] is True
        assert caps["ie_loss_review"] is True
        assert caps["product_analysis"] is True
        assert caps["availability_only"] is True

    def test_validate_output(self, sample_maven_raw):
        adapter = MavenDowntimeAdapter()
        runs = adapter.to_production_runs(sample_maven_raw)
        events = adapter.to_downtime_events(sample_maven_raw)
        result = adapter.validate_output(runs, events)

        assert result["production_runs"]["passed"] is True
        assert result["downtime_events"]["passed"] is True

    def test_load_real_data(self):
        """用真实数据文件测试完整流程。"""
        import os
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "maven")
        if not os.path.exists(os.path.join(data_path, "Manufacturing_Line_Productivity.xlsx")):
            pytest.skip("真实 Maven 数据文件不存在")

        adapter = MavenDowntimeAdapter()
        raw = adapter.load_raw(data_path)

        assert "Line productivity" in raw
        assert "Products" in raw
        assert "Downtime factors" in raw
        assert "Line downtime" in raw

        runs = adapter.to_production_runs(raw)
        events = adapter.to_downtime_events(raw)
        validation = adapter.validate_output(runs, events)

        assert len(runs) == 38
        assert len(events) > 0
        assert validation["production_runs"]["passed"] is True
        assert validation["downtime_events"]["passed"] is True
