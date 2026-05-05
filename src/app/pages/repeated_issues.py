"""Repeated Issues 页面：相似事件聚类展示。"""

import streamlit as st
import pandas as pd

from src.text.similar_events import SimilarEventRetriever
from src.metrics.loss_summary import _find_repeated_issues


def show():
    st.header("重复异常分析")

    events_df = _get_events_df()

    if events_df is None:
        st.warning("请先在「数据源管理」页面加载数据。")
        return

    if "raw_note" not in events_df.columns:
        st.warning("当前数据缺少 raw_note 字段，无法进行相似事件检索。")
        return

    valid_notes = events_df[events_df["raw_note"].notna() & (events_df["raw_note"] != "")]
    st.write(f"有效备注数量：{len(valid_notes)}")

    st.divider()

    # 关键词匹配的重复事件
    st.subheader("重复事件（关键词匹配）")
    repeated = _find_repeated_issues(events_df)
    if repeated:
        for issue in repeated:
            with st.expander(f"{issue['issue_summary']} ({issue['count']} 次, {issue['cumulative_downtime_min']:.0f} min)"):
                st.write(f"**累计停机时间**：{issue['cumulative_downtime_min']:.0f} min")
                st.write("**相关备注**：")
                for note in issue.get("evidence_notes", []):
                    st.write(f"- {note}")
    else:
        st.info("未发现重复事件")

    st.divider()

    # Embedding 相似事件检索
    st.subheader("相似事件检索（Embedding）")

    query_note = st.text_input("输入异常备注进行相似事件检索")
    top_k = st.slider("返回数量", min_value=3, max_value=10, value=5)

    if query_note and st.button("检索相似事件"):
        with st.spinner("正在构建索引并检索..."):
            try:
                retriever = SimilarEventRetriever()
                retriever.build_from_dataframe(valid_notes)
                results = retriever.find_similar(query_note, top_k=top_k)

                if results:
                    for i, r in enumerate(results, 1):
                        st.write(f"**{i}. 相似度: {r.get('similarity_score', 0):.4f}**")
                        st.write(f"- 事件 ID: {r.get('event_id', 'N/A')}")
                        st.write(f"- 原因: {r.get('raw_reason', 'N/A')}")
                        st.write(f"- 备注: {r.get('raw_note', 'N/A')}")
                        st.write(f"- 停机时间: {r.get('downtime_min', 0)} min")
                        st.divider()
                else:
                    st.info("未找到相似事件")
            except Exception as e:
                st.error(f"检索失败：{e}")
                st.info("提示：首次使用需下载 sentence-transformers 模型，可能需要较长时间。")

    st.divider()

    # Embedding 聚类
    st.subheader("相似事件聚类")
    threshold = st.slider("相似度阈值", min_value=0.5, max_value=0.95, value=0.78, step=0.01)

    if st.button("执行聚类"):
        with st.spinner("正在聚类..."):
            try:
                retriever = SimilarEventRetriever()
                retriever.build_from_dataframe(valid_notes)
                clusters = retriever.cluster_repeated_issues(valid_notes, threshold=threshold)

                if clusters:
                    st.write(f"发现 {len(clusters)} 个重复异常聚类")
                    for i, cluster in enumerate(clusters, 1):
                        with st.expander(
                            f"聚类 {i}: {cluster['cluster_summary']} "
                            f"({cluster['event_count']} 事件, {cluster['cumulative_downtime_min']:.0f} min)"
                        ):
                            st.write(f"**事件 IDs**: {', '.join(cluster['event_ids'])}")
                            st.write(f"**累计停机**: {cluster['cumulative_downtime_min']:.0f} min")
                            st.write("**样例备注**:")
                            for note in cluster.get("sample_notes", []):
                                st.write(f"- {note}")
                else:
                    st.info("未发现聚类（阈值可能过高）")
            except Exception as e:
                st.error(f"聚类失败：{e}")


def _get_events_df() -> pd.DataFrame | None:
    for key in ["gomask_events", "synthetic_events", "maven_events", "kaggle_events", "generic_events"]:
        if key in st.session_state:
            return st.session_state[key]
    if "synthetic_notes" in st.session_state:
        return st.session_state["synthetic_notes"]
    return None

show()
