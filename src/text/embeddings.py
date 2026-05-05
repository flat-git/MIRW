"""文本 Embedding 向量构建与检索。

使用 SiliconFlow API (Qwen3-Embedding-4B) 生成 embedding，
使用 numpy 余弦相似度进行检索（200 条数据无需 FAISS）。
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
from pathlib import Path
import pickle

from src.config.settings import settings


class EventEmbeddingIndex:
    """基于 SiliconFlow Embedding API 的事件文本向量检索索引。"""

    def __init__(self):
        self.api_key: str = settings.embedding.api_key
        self.base_url: str = settings.embedding.base_url
        self.model: str = settings.embedding.model
        self.dimensions: int = settings.embedding.dimensions

        self.embeddings: np.ndarray | None = None
        self.event_ids: list[str] = []
        self.texts: list[str] = []
        self.metadata: list[dict] = []

    def build_index(self, events_df: pd.DataFrame, text_col: str = "raw_note"):
        """从事件 DataFrame 构建向量索引。"""
        valid = events_df[events_df[text_col].notna() & (events_df[text_col] != "")].copy()
        if valid.empty:
            return

        self.texts = valid[text_col].tolist()
        self.event_ids = valid["event_id"].tolist() if "event_id" in valid.columns else [str(i) for i in range(len(valid))]

        # 保存元数据
        self.metadata = []
        for _, row in valid.iterrows():
            self.metadata.append({
                "event_id": row.get("event_id", ""),
                "raw_note": row.get(text_col, ""),
                "downtime_min": row.get("downtime_min", 0),
                "raw_reason": row.get("raw_reason", ""),
            })

        # 批量生成 embedding（API 支持批量）
        self.embeddings = _embed_batch(self.texts, self.api_key, self.base_url, self.model, self.dimensions)

    def search(self, query_text: str, top_k: int = 5) -> list[dict]:
        """检索最相似的事件。"""
        if self.embeddings is None or len(self.texts) == 0:
            raise ValueError("索引尚未构建，请先调用 build_index()")

        query_vec = _embed_single(query_text, self.api_key, self.base_url, self.model, self.dimensions)
        scores = _cosine_similarity(query_vec, self.embeddings)

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx].copy()
            meta["similarity_score"] = round(float(scores[idx]), 4)
            results.append(meta)

        return results

    def save(self, path: str | Path):
        """保存索引到磁盘。"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        np.save(path / "embeddings.npy", self.embeddings)
        with open(path / "metadata.pkl", "wb") as f:
            pickle.dump({
                "event_ids": self.event_ids,
                "texts": self.texts,
                "metadata": self.metadata,
                "model": self.model,
                "dimensions": self.dimensions,
            }, f)

    def load(self, path: str | Path):
        """从磁盘加载索引。"""
        path = Path(path)
        self.embeddings = np.load(path / "embeddings.npy")
        with open(path / "metadata.pkl", "rb") as f:
            data = pickle.load(f)
            self.event_ids = data["event_ids"]
            self.texts = data["texts"]
            self.metadata = data["metadata"]


def _embed_single(text: str, api_key: str, base_url: str, model: str, dimensions: int) -> np.ndarray:
    """生成单条文本的 embedding。"""
    import requests

    resp = requests.post(
        f"{base_url}/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": text, "dimensions": dimensions},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return np.array(data["data"][0]["embedding"], dtype=np.float32)


def _embed_batch(texts: list[str], api_key: str, base_url: str, model: str, dimensions: int,
                 batch_size: int = 32) -> np.ndarray:
    """批量生成 embedding（分批发送避免超长）。"""
    import requests

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = requests.post(
            f"{base_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "input": batch, "dimensions": dimensions},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # 按 index 排序确保顺序正确
        sorted_items = sorted(data["data"], key=lambda x: x["index"])
        for item in sorted_items:
            all_embeddings.append(item["embedding"])

    return np.array(all_embeddings, dtype=np.float32)


def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """计算 query 向量与矩阵中每个向量的余弦相似度。"""
    # 归一化
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    matrix_norm = matrix / matrix_norms
    return matrix_norm @ query_norm
