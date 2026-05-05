"""相似事件检索请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    use_reranker: bool = True


class SimilarEventItem(BaseModel):
    event_id: str
    raw_note: str
    raw_reason: str
    downtime_min: float
    similarity_score: float
    rerank_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SimilarEventItem]
