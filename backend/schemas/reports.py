"""报告请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel


class IeWeeklyRequest(BaseModel):
    period: str = "2024-W35"


class CapaRequest(BaseModel):
    period: str = "2024-W35"


class FiveWhyRequest(BaseModel):
    event_id: str


class ReportResponse(BaseModel):
    report_type: str
    period: str
    report_markdown: str
    check_result: dict
