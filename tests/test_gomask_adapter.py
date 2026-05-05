"""GoMask Downtime Adapter 测试。"""

import pytest
import pandas as pd

from src.adapters.gomask_downtime_adapter import GoMaskDowntimeAdapter, _parse_impact_qty


@pytest.fixture
def sample_gomask_raw():
    """构造 GoMask 格式测试数据。"""
    main = pd.DataFrame({
        "downtime_id": [1, 2, 3, 4, 5],
        "machine_id": ["MX-1001", "MX-2002", "MX-3006", "MX-4009", "MX-5003"],
        "machine_name": ["Press Alpha", "Welder Sigma", "Cutter Theta", "Press Delta", "Cutter Zeta"],
        "location": ["Assembly Line A", "Welding Bay", "Cutting Room", "Assembly Line B", "Cutting Room"],
        "downtime_start": pd.to_datetime([
            "2024-06-03T08:14:00", "2024-06-04T14:35:00", "2024-06-05T10:10:00",
            "2024-06-06T07:45:00", "2024-06-07T13:20:00",
        ]),
        "downtime_end": pd.to_datetime([
            "2024-06-03T09:02:00", "2024-06-04T15:00:00", "2024-06-05T11:30:00",
            "2024-06-06T08:15:00", "2024-06-07T15:10:00",
        ]),
        "duration_minutes": [48, 25, 80, 30, 110],
        "downtime_type": ["mechanical", "electrical", "mechanical", "operator_error", "scheduled_maintenance"],
        "cause_description": [
            "Main drive belt slipped off spindle during morning shift.",
            "Voltage drop detected; automatic shutdown triggered.",
            "Blade jammed due to improper material feed.",
            "Forgot to reset machine after maintenance break.",
            "Quarterly preventive check and calibration.",
        ],
        "resolved_by": ["tech_jroberts", "team_electric", "tech_egreen", "op_jreed", "maintenance_team"],
        "resolution_actions": [
            "Adjusted belt alignment and tension; tested startup.",
            "Reset breaker and checked wiring.",
            "Cleared jam, lubricated blade, tested cut.",
            "Restarted machine and verified settings.",
            "Cleaned and replaced filter, calibrated blade system.",
        ],
        "parts_replaced": ["belt", None, "blade", None, "filter"],
        "scheduled_maintenance": [False, False, False, False, True],
        "production_impact": [
            "24 units delayed, 48 min lost",
            "10 units lost, minor delay",
            "36 units delayed, 80 min lost",
            "No units lost, minor delay",
            "Planned downtime, no impact",
        ],
        "reported_by": ["op_cmartin", "op_rkhan", "op_dgomez", "op_jreed", "scheduler_bnelson"],
        "report_date": pd.to_datetime(["2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06", "2024-06-05"]),
    })
    return {"main": main}


class TestGoMaskDowntimeAdapter:
    def test_source_name(self):
        adapter = GoMaskDowntimeAdapter()
        assert adapter.source_name == "gomask_manufacturing_downtime"

    def test_to_production_runs(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        runs = adapter.to_production_runs(sample_gomask_raw)
        assert len(runs) > 0
        assert "run_id" in runs.columns
        assert "line_id" in runs.columns
        assert all(runs["source_dataset"] == "gomask_manufacturing_downtime")

    def test_to_downtime_events(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        events = adapter.to_downtime_events(sample_gomask_raw)
        assert len(events) == 5
        assert "event_id" in events.columns
        assert "downtime_min" in events.columns
        assert "raw_reason" in events.columns
        assert "raw_note" in events.columns

    def test_event_id_unique(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        events = adapter.to_downtime_events(sample_gomask_raw)
        assert events["event_id"].is_unique

    def test_downtime_non_negative(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        events = adapter.to_downtime_events(sample_gomask_raw)
        assert all(events["downtime_min"] > 0)

    def test_standard_loss_category_mapping(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        events = adapter.to_downtime_events(sample_gomask_raw)

        cat_map = events.set_index("raw_reason")["standard_loss_category"].to_dict()
        assert cat_map["mechanical"] == "Equipment"
        assert cat_map["electrical"] == "Equipment"
        assert cat_map["operator_error"] == "Operator"
        assert cat_map["scheduled_maintenance"] == "Changeover"

    def test_raw_note_populated(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        events = adapter.to_downtime_events(sample_gomask_raw)
        assert all(events["raw_note"].notna())
        assert all(events["raw_note"] != "")

    def test_capability_repeated_issue(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        runs = adapter.to_production_runs(sample_gomask_raw)
        events = adapter.to_downtime_events(sample_gomask_raw)
        caps = adapter.detect_capability(runs, events)
        assert caps["repeated_issue_retrieval"] == True
        assert caps["resolution_tracking"] == True
        assert caps["machine_analysis"] == True

    def test_validate_output(self, sample_gomask_raw):
        adapter = GoMaskDowntimeAdapter()
        runs = adapter.to_production_runs(sample_gomask_raw)
        events = adapter.to_downtime_events(sample_gomask_raw)
        result = adapter.validate_output(runs, events)
        assert result["production_runs"]["passed"] is True
        assert result["downtime_events"]["passed"] is True

    def test_load_real_data(self):
        """端到端测试真实 GoMask 数据。"""
        import os
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "gomask")
        if not os.path.exists(os.path.join(data_path, "manufacturing-machine-downtime-logs.csv")):
            pytest.skip("真实 GoMask 数据文件不存在")

        adapter = GoMaskDowntimeAdapter()
        raw = adapter.load_raw(data_path)
        assert "main" in raw
        assert len(raw["main"]) == 200

        runs = adapter.to_production_runs(raw)
        events = adapter.to_downtime_events(raw)
        validation = adapter.validate_output(runs, events)

        assert len(events) == 200
        assert validation["production_runs"]["passed"] is True
        assert validation["downtime_events"]["passed"] is True


class TestParseImpactQty:
    def test_units_delayed(self):
        assert _parse_impact_qty("24 units delayed, 48 min lost") == 24

    def test_units_lost(self):
        assert _parse_impact_qty("10 units lost, minor delay") == 10

    def test_no_impact(self):
        assert _parse_impact_qty("No impact") == 0

    def test_planned_downtime(self):
        assert _parse_impact_qty("Planned downtime, no impact") == 0

    def test_none_text(self):
        assert _parse_impact_qty("") == 0
        assert _parse_impact_qty("All production suspended") == 0

    def test_lab_test(self):
        assert _parse_impact_qty("Lab test; no production affected") == 0
