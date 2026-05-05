"""Quality Dashboard 页面：质量异常、scrap、CAPA 状态。"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.metrics.quality import scrap_rate, quality_related_downtime, quality_issue_pareto, quality_issue_recurrence


def show():
    st.header("质量异常分析看板")

    events_df = _get_events_df()
    runs_df = _get_runs_df()

    if events_df is None:
        st.warning("请先在「数据源管理」页面加载数据。")
        return

    # 质量指标摘要
    qdt = quality_related_downtime(events_df)
    sr = scrap_rate(runs_df) if runs_df is not None else {"scrap_rate": None}

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("质量相关停机", f"{qdt.get('quality_downtime_min', 0):.0f} min")
    with col2:
        if sr.get("scrap_rate") is not None:
            st.metric("废品率", f"{sr['scrap_rate']:.2%}")
        else:
            st.metric("废品率", "N/A")
            st.caption("当前数据缺少 scrap_output 字段，因此不展示 scrap rate。")
    with col3:
        st.metric("质量事件数", f"{qdt.get('quality_event_count', 0)}")

    st.divider()

    # 质量异常 Pareto
    st.subheader("质量异常 Pareto")
    qpareto = quality_issue_pareto(events_df)
    if not qpareto.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=qpareto["issue"],
            y=qpareto["impact_min"],
            name="影响时间 (min)",
            marker_color="coral",
        ))
        fig.update_layout(
            xaxis_title="质量异常类别",
            yaxis_title="影响时间 (min)",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(qpareto)
    else:
        st.info("无质量相关异常数据")

    st.divider()

    # 重复质量异常
    st.subheader("重复质量异常")
    recurrence = quality_issue_recurrence(events_df)
    if recurrence:
        recur_df = pd.DataFrame(recurrence)
        st.dataframe(recur_df)

        fig = px.bar(recur_df, x="issue", y="count", color="total_downtime_min",
                     title="重复质量异常次数")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("未发现重复质量异常")

    st.divider()

    # CAPA 状态（如果有 action items）
    st.subheader("CAPA 状态")
    if "action_items" in st.session_state:
        actions_df = st.session_state["action_items"]
        from src.actions.action_tracker import ActionTracker
        tracker = ActionTracker(actions_df)
        summary = tracker.summary_by_status()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Open", summary.get("Open", 0))
        with col2:
            st.metric("In Progress", summary.get("In Progress", 0))
        with col3:
            st.metric("Closed", summary.get("Closed", 0))

        overdue = tracker.get_overdue()
        if not overdue.empty:
            st.warning(f"超期改善项：{len(overdue)} 条")
            st.dataframe(overdue)
    else:
        st.info("未加载改善项数据。请在「合成数据 Demo」中加载。")


def _get_events_df() -> pd.DataFrame | None:
    for key in ["gomask_events", "synthetic_events", "maven_events", "kaggle_events", "generic_events"]:
        if key in st.session_state:
            return st.session_state[key]
    if "synthetic_notes" in st.session_state:
        return st.session_state["synthetic_notes"]
    return None


def _get_runs_df() -> pd.DataFrame | None:
    for key in ["maven_runs", "kaggle_runs", "generic_runs"]:
        if key in st.session_state:
            return st.session_state[key]
    return None

show()
