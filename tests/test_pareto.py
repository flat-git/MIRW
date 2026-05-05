"""Pareto 分析测试。"""

import pytest
import pandas as pd

from src.metrics.pareto import top_loss_pareto, pareto_chart_data


@pytest.fixture
def sample_events():
    return pd.DataFrame({
        "event_id": [f"E{i:03d}" for i in range(1, 8)],
        "source_dataset": ["test"] * 7,
        "downtime_min": [120, 80, 60, 40, 30, 20, 10],
        "raw_reason": ["Equipment", "Material", "Quality", "Equipment", "Changeover", "Material", "Operator"],
        "standard_loss_category": ["Equipment", "Material", "Quality", "Equipment", "Changeover", "Material", "Operator"],
    })


class TestPareto:
    def test_top_loss_pareto(self, sample_events):
        pareto = top_loss_pareto(sample_events)

        assert len(pareto) == 5  # 默认 top_n=10，但只有 5 个类别
        # 第一名应该是 Equipment (120+40=160)
        assert pareto.iloc[0]["category"] == "Equipment"
        assert pareto.iloc[0]["total_downtime_min"] == 160

    def test_cumulative_ratio_reaches_one(self, sample_events):
        pareto = top_loss_pareto(sample_events)
        # 最后一行的累计比率应该接近 1.0
        assert pareto.iloc[-1]["cumulative_ratio"] == pytest.approx(1.0, rel=1e-2)

    def test_ranking_order(self, sample_events):
        pareto = top_loss_pareto(sample_events)
        values = pareto["total_downtime_min"].tolist()
        # 应该是降序
        assert values == sorted(values, reverse=True)

    def test_pareto_chart_data(self, sample_events):
        data = pareto_chart_data(sample_events)
        assert "categories" in data
        assert "values" in data
        assert "cumulative_ratios" in data
        assert len(data["categories"]) > 0

    def test_empty_events(self):
        df = pd.DataFrame(columns=["event_id", "downtime_min", "raw_reason"])
        pareto = top_loss_pareto(df)
        assert pareto.empty

    def test_top_n_limit(self, sample_events):
        pareto = top_loss_pareto(sample_events, top_n=2)
        assert len(pareto) == 2
