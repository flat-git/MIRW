"""数据源请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel


class DatasetLoadRequest(BaseModel):
    source: str  # "maven" | "gomask" | "kaggle" | "synthetic"


class DatasetSummary(BaseModel):
    dataset_id: str
    source: str
    run_count: int
    event_count: int
    loaded_at: str
    capability: dict
    validation: dict


class DatasetListItem(BaseModel):
    dataset_id: str
    source: str
    run_count: int
    event_count: int
    loaded_at: str
