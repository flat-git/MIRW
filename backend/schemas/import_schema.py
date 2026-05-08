"""导入流程请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    analysis_id: str
    file_name: str
    total_rows: int
    columns: list[dict]
    suggested_mappings: list[dict]
    unmapped_columns: list[str]
    detected_structure: str


class ImportMapping(BaseModel):
    source_column: str
    target_field: str | None = None


class ImportRequest(BaseModel):
    analysis_id: str
    confirmed_mappings: list[ImportMapping]
    deduplicate: bool = True
    normalize_nulls: bool = True
    coerce_types: bool = True


class ImportResult(BaseModel):
    dataset_id: str
    source: str
    run_count: int
    event_count: int
    cleaning_report: dict
    capability: dict
    validation: dict
