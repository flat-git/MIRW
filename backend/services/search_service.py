"""相似事件检索服务。调用 src/text 检索。"""

from __future__ import annotations

from backend.state import store


def search_similar_events(dataset_id: str, query: str, top_k: int = 5,
                          use_reranker: bool = True) -> list[dict]:
    """检索相似事件。"""
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    events_df = ds["events_df"]
    if "raw_note" not in events_df.columns:
        raise ValueError(f"数据集 {dataset_id} 无 raw_note 字段，不支持相似事件检索")
    valid = events_df[events_df["raw_note"].notna() & (events_df["raw_note"] != "")]
    if len(valid) == 0:
        raise ValueError(f"数据集 {dataset_id} 的 raw_note 全部为空，不支持相似事件检索")

    retriever = store.get_or_build_index(dataset_id)
    results = retriever.find_similar(query, top_k=top_k, use_reranker=use_reranker)
    return results

