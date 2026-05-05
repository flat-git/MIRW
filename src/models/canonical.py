"""统一制造异常事件模型。所有数据源最终映射到此模型。"""

from datetime import date, datetime
from pydantic import BaseModel, Field


class ProductionRun(BaseModel):
    """生产批次记录。"""

    run_id: str
    source_dataset: str

    line_id: str | None = None
    machine_id: str | None = None
    product_id: str | None = None
    operator_id: str | None = None
    shift: str | None = None

    planned_start: datetime | None = None
    planned_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None

    planned_time_min: float | None = None
    runtime_min: float | None = None
    downtime_min: float | None = None

    target_output: float | None = None
    actual_output: float | None = None
    good_output: float | None = None
    scrap_output: float | None = None

    metadata: dict = Field(default_factory=dict)


class DowntimeEvent(BaseModel):
    """停机/异常事件记录。"""

    event_id: str
    run_id: str | None = None
    source_dataset: str

    line_id: str | None = None
    machine_id: str | None = None
    product_id: str | None = None
    operator_id: str | None = None
    shift: str | None = None

    event_start: datetime | None = None
    event_end: datetime | None = None
    downtime_min: float

    raw_reason: str
    standard_loss_category: str | None = None
    responsible_area: str | None = None
    raw_note: str | None = None
    evidence_text: str | None = None

    is_synthetic_note: bool = False
    metadata: dict = Field(default_factory=dict)


class IssueReview(BaseModel):
    """复盘与改善项记录。"""

    issue_id: str
    event_id: str | None = None

    issue_summary: str
    issue_type: str
    impact_type: str | None = None
    impact_minutes: float | None = None
    impact_qty: float | None = None

    candidate_root_cause: str | None = None
    temporary_action: str | None = None
    permanent_action: str | None = None

    owner: str | None = None
    status: str = "Open"
    due_date: date | None = None
    close_date: date | None = None

    recurrence_flag: bool = False
    human_confirmed: bool = False
    evidence_text: str | None = None

    metadata: dict = Field(default_factory=dict)
