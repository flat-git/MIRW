"""效率指标测试。"""

import pytest
import pandas as pd

from src.metrics.efficiency import calculate_downtime_ratio, calculate_line_efficiency


@pytest.fixture
def sample_runs():
    return pd.DataFrame({
        "run_id": ["R001", "R002"],
        "planned_time_min": [480.0, 480.0],
        "runtime_min": [420.0, 450.0],
        "downtime_min": [60.0, 30.0],
    })


class TestEfficiency:
    def test_downtime_ratio(self, sample_runs):
        result = calculate_downtime_ratio(sample_runs)
        # (60+30) / (480+480) = 90/960
        assert result["downtime_ratio"] == pytest.approx(90 / 960, rel=1e-3)
        assert result["total_downtime_min"] == 90.0
        assert result["total_planned_min"] == 960.0

    def test_line_efficiency(self, sample_runs):
        result = calculate_line_efficiency(sample_runs)
        # (420+450) / (480+480) = 870/960
        assert result["line_efficiency"] == pytest.approx(870 / 960, rel=1e-3)

    def test_missing_columns(self):
        df = pd.DataFrame({"run_id": ["R001"]})
        result = calculate_downtime_ratio(df)
        assert result["downtime_ratio"] is None

    def test_zero_planned_time(self):
        df = pd.DataFrame({"planned_time_min": [0.0], "downtime_min": [10.0]})
        result = calculate_downtime_ratio(df)
        assert result["downtime_ratio"] is None
