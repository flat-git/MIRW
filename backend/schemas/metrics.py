"""指标请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel


class EfficiencySummary(BaseModel):
    total_downtime_min: float | None = None
    total_planned_min: float | None = None
    total_runtime_min: float | None = None
    downtime_ratio: float | None = None
    line_efficiency: float | None = None
    total_runs: int = 0
    total_events: int = 0


class ParetoItem(BaseModel):
    category: str
    total_downtime_min: float
    event_count: int
    ratio: float
    cumulative_ratio: float


class DowntimeGroupItem(BaseModel):
    group_key: str
    total_downtime_min: float
    event_count: int
    ratio: float
