"""改善项请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel


class ActionItem(BaseModel):
    action_id: str
    related_event_id: str | None = None
    problem: str
    temporary_action: str | None = None
    permanent_action: str | None = None
    owner: str | None = None
    due_date: str | None = None
    status: str = "Open"
    close_date: str | None = None
    recurrence_flag: bool = False


class ActionSummary(BaseModel):
    total: int
    open: int
    in_progress: int
    closed: int
    overdue: int
    recurred: int
