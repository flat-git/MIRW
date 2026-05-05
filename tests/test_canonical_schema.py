"""Pydantic 模型校验测试。"""

import pytest
from datetime import datetime, date

from src.models.canonical import ProductionRun, DowntimeEvent, IssueReview


class TestProductionRun:
    def test_minimal_valid(self):
        run = ProductionRun(run_id="R001", source_dataset="test")
        assert run.run_id == "R001"
        assert run.source_dataset == "test"
        assert run.line_id is None

    def test_full_fields(self):
        run = ProductionRun(
            run_id="R001",
            source_dataset="test",
            line_id="L01",
            machine_id="M01",
            product_id="P01",
            planned_time_min=480.0,
            runtime_min=420.0,
            downtime_min=60.0,
            target_output=1000,
            actual_output=950,
            good_output=930,
            scrap_output=20,
        )
        assert run.planned_time_min == 480.0
        assert run.good_output == 930

    def test_metadata_default(self):
        run = ProductionRun(run_id="R001", source_dataset="test")
        assert run.metadata == {}


class TestDowntimeEvent:
    def test_minimal_valid(self):
        event = DowntimeEvent(
            event_id="E001",
            source_dataset="test",
            downtime_min=30.0,
            raw_reason="Equipment fault",
        )
        assert event.event_id == "E001"
        assert event.downtime_min == 30.0

    def test_negative_downtime_allowed_in_model(self):
        """Pydantic 模型本身不禁止负值，由 validate_schema 检查。"""
        event = DowntimeEvent(
            event_id="E001",
            source_dataset="test",
            downtime_min=-5.0,
            raw_reason="Test",
        )
        assert event.downtime_min == -5.0

    def test_synthetic_flag(self):
        event = DowntimeEvent(
            event_id="E001",
            source_dataset="synthetic",
            downtime_min=10.0,
            raw_reason="Test",
            is_synthetic_note=True,
        )
        assert event.is_synthetic_note is True


class TestIssueReview:
    def test_default_status(self):
        issue = IssueReview(
            issue_id="I001",
            issue_summary="Test issue",
            issue_type="Equipment",
        )
        assert issue.status == "Open"
        assert issue.recurrence_flag is False

    def test_full_fields(self):
        issue = IssueReview(
            issue_id="I001",
            issue_summary="吸嘴堵塞",
            issue_type="Equipment",
            impact_minutes=22.0,
            temporary_action="更换吸嘴",
            owner="李工",
            due_date=date(2026, 5, 10),
        )
        assert issue.owner == "李工"
        assert issue.due_date == date(2026, 5, 10)
