"""数据源适配器基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from src.data.validate_schema import ValidationResult


class BaseAdapter(ABC):
    """所有数据源适配器的基类。"""

    source_name: str = "base"

    @abstractmethod
    def load_raw(self, path: str | Path) -> dict[str, pd.DataFrame]:
        """加载原始数据文件。

        返回 dict，key 为数据表名，value 为 DataFrame。
        """
        ...

    @abstractmethod
    def to_production_runs(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将原始数据映射为标准 production_run 表。"""
        ...

    @abstractmethod
    def to_downtime_events(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将原始数据映射为标准 downtime_event 表。"""
        ...

    def detect_capability(self, runs: pd.DataFrame, events: pd.DataFrame) -> dict[str, bool]:
        """检测当前数据支持哪些分析能力。"""
        caps = {
            "downtime_pareto": "downtime_min" in events.columns and "raw_reason" in events.columns,
            "ie_loss_review": "downtime_min" in events.columns,
            "repeated_issue_retrieval": "raw_note" in events.columns,
            "full_oee": all(
                col in runs.columns
                for col in ["planned_time_min", "runtime_min", "actual_output", "good_output"]
            ),
            "availability_only": all(
                col in runs.columns for col in ["planned_time_min", "runtime_min"]
            ),
            "quality_rate": "good_output" in runs.columns and "actual_output" in runs.columns,
            "scrap_rate": "scrap_output" in runs.columns,
            "shift_analysis": "shift" in events.columns,
            "operator_analysis": "operator_id" in events.columns,
            "product_analysis": "product_id" in events.columns,
        }
        missing = []
        if not caps["full_oee"]:
            for col in ["planned_time_min", "runtime_min", "actual_output", "good_output", "ideal_cycle_time"]:
                if col not in runs.columns:
                    missing.append(col)
        caps["missing_fields"] = missing
        return caps

    def validate_output(self, runs: pd.DataFrame, events: pd.DataFrame) -> dict:
        """校验适配器输出。"""
        from src.data.validate_schema import validate_production_runs, validate_downtime_events

        runs_result = validate_production_runs(runs)
        events_result = validate_downtime_events(events)
        capability = self.detect_capability(runs, events)

        return {
            "source": self.source_name,
            "production_runs": {
                "passed": runs_result.passed,
                "errors": runs_result.errors,
                "stats": runs_result.stats,
            },
            "downtime_events": {
                "passed": events_result.passed,
                "errors": events_result.errors,
                "stats": events_result.stats,
            },
            "capability": capability,
        }
