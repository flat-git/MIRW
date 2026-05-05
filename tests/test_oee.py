"""OEE 计算测试。手工构造小样本验证。"""

import pytest
import pandas as pd

from src.metrics.oee import calculate_oee, calculate_aggregate_oee


@pytest.fixture
def sample_runs():
    """手工构造的测试数据。"""
    return pd.DataFrame({
        "run_id": ["R001", "R002"],
        "source_dataset": ["test", "test"],
        "planned_time_min": [480.0, 480.0],
        "runtime_min": [420.0, 450.0],
        "downtime_min": [60.0, 30.0],
        "actual_output": [950.0, 1000.0],
        "good_output": [930.0, 980.0],
        "scrap_output": [20.0, 20.0],
    })


class TestOEE:
    def test_single_oee_without_ideal_cycle_time(self, sample_runs):
        """没有 ideal_cycle_time 时不应输出 Performance。"""
        results = calculate_oee(sample_runs)

        r0 = results[0]
        assert r0["availability"] == pytest.approx(420 / 480, rel=1e-3)
        assert r0["performance"] is None
        assert r0["quality"] == pytest.approx(930 / 950, rel=1e-3)
        assert r0["oee"] is None  # 缺 Performance 不能算 OEE
        assert r0["capability"]["full_oee"] is False
        assert "ideal_cycle_time" in r0["capability"]["missing_fields"]

    def test_aggregate_oee(self, sample_runs):
        agg = calculate_aggregate_oee(sample_runs)

        # Availability = (420+450) / (480+480) = 870/960
        assert agg["availability"] == pytest.approx(870 / 960, rel=1e-3)

        # Quality = (930+980) / (950+1000) = 1910/1950
        assert agg["quality"] == pytest.approx(1910 / 1950, rel=1e-3)

        # Performance 应为 None
        assert agg["performance"] is None
        assert agg["oee"] is None

    def test_oee_with_ideal_cycle_time(self):
        """有 ideal_cycle_time 时应该输出完整 OEE。"""
        runs = pd.DataFrame({
            "run_id": ["R001"],
            "source_dataset": ["test"],
            "planned_time_min": [480.0],
            "runtime_min": [450.0],
            "actual_output": [1000.0],
            "good_output": [980.0],
            "ideal_cycle_time": [0.45],  # 0.45 min per unit
        })

        results = calculate_oee(runs)
        r0 = results[0]

        # Availability = 450/480 = 0.9375
        assert r0["availability"] == pytest.approx(0.9375, rel=1e-3)
        # Performance = 0.45 * 1000 / 450 = 1.0
        assert r0["performance"] == pytest.approx(1.0, rel=1e-3)
        # Quality = 980/1000 = 0.98
        assert r0["quality"] == pytest.approx(0.98, rel=1e-3)
        # OEE = 0.9375 * 1.0 * 0.98
        assert r0["oee"] == pytest.approx(0.9375 * 1.0 * 0.98, rel=1e-3)
        assert r0["capability"]["full_oee"] is True

    def test_empty_dataframe(self):
        runs = pd.DataFrame(columns=["run_id", "source_dataset"])
        results = calculate_oee(runs)
        assert results == []
