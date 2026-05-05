"""相似事件检索与重复异常聚类。

流程：Embedding 粗筛（top_k*3） → Reranker 精排（top_k）
"""

from __future__ import annotations

import pandas as pd

from src.text.embeddings import EventEmbeddingIndex
from src.text.reranker import rerank_events


class SimilarEventRetriever:
    """相似事件检索器（Embedding 粗筛 + Reranker 精排）。"""

    def __init__(self):
        self.index = EventEmbeddingIndex()
        self._built = False

    def build_from_dataframe(self, events_df: pd.DataFrame, text_col: str = "raw_note"):
        """从事件 DataFrame 构建检索索引。"""
        self.index.build_index(events_df, text_col)
        self._built = True

    def find_similar(self, query_note: str, top_k: int = 5, use_reranker: bool = True) -> list[dict]:
        """查找相似事件。

        Args:
            query_note: 查询备注文本
            top_k: 最终返回数量
            use_reranker: 是否启用 reranker 精排
        """
        if not self._built:
            raise ValueError("索引尚未构建，请先调用 build_from_dataframe()")

        if use_reranker:
            # 粗筛取 top_k*3，然后 rerank 精排取 top_k
            candidates = self.index.search(query_note, top_k=top_k * 3)
            return rerank_events(query_note, candidates, text_key="raw_note", top_n=top_k)
        else:
            return self.index.search(query_note, top_k=top_k)

    def cluster_repeated_issues(self, events_df: pd.DataFrame, threshold: float = 0.65,
                                text_col: str = "raw_note") -> list[dict]:
        """聚类重复发生的异常。

        使用 embedding 相似度将相似事件归为一组。
        """
        if not self._built:
            self.build_from_dataframe(events_df, text_col)

        valid = events_df[events_df[text_col].notna() & (events_df[text_col] != "")].copy()
        if valid.empty:
            return []

        clusters: list[dict] = []
        assigned: set[int] = set()

        for i, (_, row) in enumerate(valid.iterrows()):
            if i in assigned:
                continue

            note = row[text_col]
            similar = self.index.search(note, top_k=10)

            cluster_event_ids = [row["event_id"]] if "event_id" in valid.columns else [str(i)]
            cluster_notes = [note]
            cluster_downtime = float(row.get("downtime_min", 0))

            for sim in similar:
                sim_score = sim.get("similarity_score", 0)
                if sim_score < threshold:
                    continue
                sim_id = sim.get("event_id", "")
                if "event_id" in valid.columns:
                    match = valid[valid["event_id"] == sim_id]
                    if not match.empty:
                        idx = match.index[0]
                        pos = valid.index.get_loc(idx)
                        if pos not in assigned and sim_id not in cluster_event_ids:
                            cluster_event_ids.append(sim_id)
                            cluster_notes.append(sim.get("raw_note", ""))
                            cluster_downtime += float(match.iloc[0].get("downtime_min", 0))
                            assigned.add(pos)

            if len(cluster_event_ids) >= 2:
                clusters.append({
                    "cluster_summary": note[:80],
                    "event_count": len(cluster_event_ids),
                    "event_ids": cluster_event_ids,
                    "cumulative_downtime_min": round(cluster_downtime, 1),
                    "sample_notes": cluster_notes[:3],
                })

            assigned.add(i)

        clusters.sort(key=lambda x: x["event_count"], reverse=True)
        return clusters


def retrieve_similar_events(events_df: pd.DataFrame, query_note: str,
                            top_k: int = 5) -> list[dict]:
    """便捷函数：从事件 DataFrame 中检索相似事件。"""
    retriever = SimilarEventRetriever()
    retriever.build_from_dataframe(events_df)
    return retriever.find_similar(query_note, top_k)
