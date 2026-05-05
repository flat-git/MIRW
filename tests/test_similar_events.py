"""相似事件检索测试（使用 SiliconFlow API）。

需要有效的 EMBEDDING_API_KEY 才能运行。
无 API key 时自动 skip。
"""

import os
import pytest
import pandas as pd

HAS_API_KEY = bool(os.getenv("EMBEDDING_API_KEY", ""))
RUN_LIVE_EMBEDDING_TESTS = os.getenv("MIRW_LIVE_EMBEDDING_TESTS", "").lower() in {"1", "true", "yes"}

from src.text.similar_events import SimilarEventRetriever


# 10 组同义异常（每组内语义相近）
SYNONYM_GROUPS = [
    ["Press motor overheated and tripped safety cutoff.", "Motor thermal protection activated during run.", "Main drive motor shut down due to overheating."],
    ["Belt slipped off spindle during morning shift.", "Drive belt misalignment caused machine stoppage.", "Conveyor belt came loose from roller."],
    ["Voltage drop detected, automatic shutdown triggered.", "Electrical surge caused machine to power off.", "Power fluctuation led to emergency stop."],
    ["Blade jammed due to improper material feed.", "Cutting blade stuck from material misalignment.", "Blade dulled and could not cut through stock."],
    ["Operator forgot to reset machine after break.", "Machine settings not restored after maintenance.", "Operator error: wrong recipe loaded for batch."],
    ["Quarterly preventive check and calibration.", "Scheduled maintenance window for filter change.", "Planned downtime for equipment inspection."],
    ["Welding torch tip clogged, replaced nozzle.", "Welding wire feed jammed in guide tube.", "Welding gas flow interrupted, replaced regulator."],
    ["Hydraulic pressure loss in press unit.", "Hydraulic fluid leak detected under press.", "Press cylinder seal failed, fluid spraying."],
    ["Sensor misreading caused conveyor stop.", "Proximity sensor out of alignment, realigned.", "Photo-eye sensor dirty, cleaned and restarted."],
    ["Bearing seized on main drive shaft.", "Bearing noise detected, preemptive replacement.", "Drive shaft bearing overheated, shutdown for cooling."],
]


@pytest.fixture
def events_df():
    """构造测试事件 DataFrame。"""
    rows = []
    event_id = 1
    for group_idx, group in enumerate(SYNONYM_GROUPS):
        for note in group:
            rows.append({
                "event_id": f"E{event_id:03d}",
                "source_dataset": "test",
                "downtime_min": 20 + group_idx * 5,
                "raw_reason": f"Reason_{group_idx + 1}",
                "raw_note": note,
            })
            event_id += 1
    return pd.DataFrame(rows)


@pytest.mark.skipif(
    not HAS_API_KEY or not RUN_LIVE_EMBEDDING_TESTS,
    reason="需要设置 EMBEDDING_API_KEY 且 MIRW_LIVE_EMBEDDING_TESTS=1 才运行在线 embedding 测试",
)
class TestSimilarEvents:
    def test_build_index(self, events_df):
        """测试索引构建。"""
        retriever = SimilarEventRetriever()
        retriever.build_from_dataframe(events_df)
        assert retriever._built is True
        assert len(retriever.index.texts) == len(events_df)

    def test_find_similar_returns_results(self, events_df):
        """测试相似事件检索返回结果。"""
        retriever = SimilarEventRetriever()
        retriever.build_from_dataframe(events_df)
        results = retriever.find_similar("motor overheating issue", top_k=3, use_reranker=False)

        assert len(results) > 0
        assert "similarity_score" in results[0]
        assert "event_id" in results[0]

    def test_similar_notes_ranked_by_score(self, events_df):
        """测试相似事件按分数排序。"""
        retriever = SimilarEventRetriever()
        retriever.build_from_dataframe(events_df)
        results = retriever.find_similar("motor overheated and shut down", top_k=5, use_reranker=False)

        scores = [r["similarity_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_find_similar_with_reranker(self, events_df):
        """测试 embedding + reranker 两阶段检索。"""
        retriever = SimilarEventRetriever()
        retriever.build_from_dataframe(events_df)
        results = retriever.find_similar("motor overheating", top_k=3, use_reranker=True)

        assert len(results) > 0
        assert "rerank_score" in results[0]
        rerank_scores = [r["rerank_score"] for r in results]
        assert rerank_scores == sorted(rerank_scores, reverse=True)

    def test_recall_at_3(self, events_df):
        """Recall@3 测试：查询同组内容，前 3 结果中应包含同组事件。"""
        retriever = SimilarEventRetriever()
        retriever.build_from_dataframe(events_df)

        hits = 0
        total = 0
        for group in SYNONYM_GROUPS[:5]:
            query = group[0]
            total += 1
            results = retriever.find_similar(query, top_k=3, use_reranker=False)
            result_notes = [r.get("raw_note", "") for r in results]
            for other_note in group[1:]:
                if any(other_note in rn or rn in other_note for rn in result_notes):
                    hits += 1
                    break

        recall_at_3 = hits / total if total > 0 else 0
        assert recall_at_3 >= 0.6

    def test_empty_note_filtered(self):
        """空备注应被过滤。"""
        df = pd.DataFrame({
            "event_id": ["E001", "E002"],
            "source_dataset": ["test", "test"],
            "downtime_min": [10, 20],
            "raw_reason": ["A", "B"],
            "raw_note": ["motor failure", ""],
        })
        retriever = SimilarEventRetriever()
        retriever.build_from_dataframe(df)
        assert len(retriever.index.texts) == 1
