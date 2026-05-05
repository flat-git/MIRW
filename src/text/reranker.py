"""Reranker 模块：使用 SiliconFlow Qwen3-Reranker-4B 对检索结果重排。"""

from __future__ import annotations

import requests

from src.config.settings import settings


def rerank(query: str, documents: list[str], top_n: int = 5) -> list[dict]:
    """使用 Reranker 模型对文档进行重排序。

    Args:
        query: 查询文本
        documents: 候选文档列表
        top_n: 返回前 n 个结果

    Returns:
        [{"index": int, "relevance_score": float}, ...] 按分数降序
    """
    if not documents:
        return []

    api_key = settings.embedding.api_key
    base_url = settings.embedding.base_url
    model = settings.embedding.reranker_model

    resp = requests.post(
        f"{base_url}/rerank",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "query": query,
            "documents": documents,
            "top_n": top_n,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def rerank_events(query: str, candidates: list[dict], text_key: str = "raw_note",
                  top_n: int = 5) -> list[dict]:
    """对候选事件进行重排序，保留原始元数据。

    Args:
        query: 查询文本
        candidates: 候选事件列表（每个是 dict，包含 text_key 字段）
        text_key: 用于 rerank 的文本字段名
        top_n: 返回前 n 个结果

    Returns:
        候选事件列表，添加 rerank_score 字段，按 rerank 分数降序
    """
    if not candidates:
        return []

    documents = [c.get(text_key, "") for c in candidates]
    rerank_results = rerank(query, documents, top_n=top_n)

    # 组装结果
    reranked = []
    for r in rerank_results:
        idx = r["index"]
        if 0 <= idx < len(candidates):
            item = candidates[idx].copy()
            item["rerank_score"] = round(r["relevance_score"], 4)
            reranked.append(item)

    # 按 rerank 分数降序
    reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return reranked
