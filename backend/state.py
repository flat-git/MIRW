"""内存数据集缓存，替代 Streamlit session_state。"""

from __future__ import annotations

import uuid
from datetime import datetime
from threading import Lock

import pandas as pd

from src.text.similar_events import SimilarEventRetriever


class DatasetStore:
    """全局数据集存储（线程安全）。"""

    _datasets: dict[str, dict] = {}
    _search_indexes: dict[str, SimilarEventRetriever] = {}
    _reports: dict[str, list[dict]] = {}  # dataset_id → [report, ...]
    _lock = Lock()

    @classmethod
    def store(cls, dataset_id: str, runs_df: pd.DataFrame, events_df: pd.DataFrame,
              validation: dict, source: str, pipeline: dict | None = None,
              actions_df: pd.DataFrame | None = None) -> None:
        with cls._lock:
            cls._datasets[dataset_id] = {
                "dataset_id": dataset_id,
                "source": source,
                "runs_df": runs_df,
                "events_df": events_df,
                "validation": validation,
                "pipeline": pipeline or {},
                "actions_df": actions_df,
                "loaded_at": datetime.now().isoformat(),
                "run_count": len(runs_df),
                "event_count": len(events_df),
            }

    @classmethod
    def get(cls, dataset_id: str) -> dict | None:
        return cls._datasets.get(dataset_id)

    @classmethod
    def list_datasets(cls) -> list[dict]:
        latest_by_source = {}
        for d in cls._datasets.values():
            current = latest_by_source.get(d["source"])
            if current is None or d["loaded_at"] > current["loaded_at"]:
                latest_by_source[d["source"]] = d

        latest = sorted(latest_by_source.values(), key=lambda d: d["loaded_at"], reverse=True)
        return [
            {
                "dataset_id": d["dataset_id"],
                "source": d["source"],
                "run_count": d["run_count"],
                "event_count": d["event_count"],
                "loaded_at": d["loaded_at"],
                "validation_passed": (
                    d.get("validation", {}).get("production_runs", {}).get("passed", True)
                    and d.get("validation", {}).get("downtime_events", {}).get("passed", True)
                ),
            }
            for d in latest
        ]

    @classmethod
    def get_or_build_index(cls, dataset_id: str) -> SimilarEventRetriever:
        """获取或构建相似事件检索索引。"""
        if dataset_id not in cls._search_indexes:
            ds = cls.get(dataset_id)
            if ds is None:
                raise ValueError(f"数据集 {dataset_id} 不存在")
            retriever = SimilarEventRetriever()
            retriever.build_from_dataframe(ds["events_df"])
            cls._search_indexes[dataset_id] = retriever
        return cls._search_indexes[dataset_id]

    @classmethod
    def store_report(cls, dataset_id: str, report: dict) -> dict:
        """保存生成的报告到历史记录。"""
        report_id = uuid.uuid4().hex[:8]
        report["report_id"] = report_id
        report["generated_at"] = datetime.now().isoformat()
        with cls._lock:
            if dataset_id not in cls._reports:
                cls._reports[dataset_id] = []
            cls._reports[dataset_id].append(report)
        return report

    @classmethod
    def list_reports(cls, dataset_id: str) -> list[dict]:
        """获取数据集的报告历史。"""
        return cls._reports.get(dataset_id, [])

    @classmethod
    def get_report(cls, dataset_id: str, report_id: str) -> dict | None:
        """获取单份报告。"""
        for r in cls._reports.get(dataset_id, []):
            if r.get("report_id") == report_id:
                return r
        return None

    @classmethod
    def generate_id(cls) -> str:
        return uuid.uuid4().hex[:8]


store = DatasetStore()
