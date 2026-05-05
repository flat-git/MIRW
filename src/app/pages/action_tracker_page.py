"""Action Tracker 页面：改善项闭环跟踪。"""

import streamlit as st
import plotly.express as px
import pandas as pd

from src.actions.action_tracker import ActionTracker
from src.data.sample_data import load_synthetic_action_items


def show():
    st.header("改善项闭环跟踪")

    # 加载改善项数据
    if "action_items" not in st.session_state:
        if st.button("加载合成改善项数据"):
            try:
                actions = load_synthetic_action_items()
                st.session_state["action_items"] = actions
                st.success(f"加载成功，共 {len(actions)} 条改善项")
            except Exception as e:
                st.error(f"加载失败：{e}")

    if "action_items" not in st.session_state:
        st.info("请加载改善项数据。")
        return

    actions_df = st.session_state["action_items"]
    tracker = ActionTracker(actions_df)

    # 状态汇总
    st.subheader("状态分布")
    summary = tracker.summary_by_status()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", summary.get("total", 0))
    with col2:
        st.metric("Open", summary.get("Open", 0))
    with col3:
        st.metric("In Progress", summary.get("In Progress", 0))
    with col4:
        st.metric("Closed", summary.get("Closed", 0))

    # 状态饼图
    fig = px.pie(
        names=["Open", "In Progress", "Closed"],
        values=[summary.get("Open", 0), summary.get("In Progress", 0), summary.get("Closed", 0)],
        title="状态分布",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 超期项
    st.subheader("超期改善项")
    overdue = tracker.get_overdue()
    if not overdue.empty:
        st.warning(f"共 {len(overdue)} 条超期")
        st.dataframe(overdue)
    else:
        st.success("无超期改善项")

    st.divider()

    # 关闭后复发
    st.subheader("关闭后复发项")
    recurred = tracker.get_recurred()
    if not recurred.empty:
        st.error(f"共 {len(recurred)} 条复发")
        st.dataframe(recurred)
    else:
        st.success("无复发项")

    st.divider()

    # 按负责人汇总
    st.subheader("按负责人汇总")
    by_owner = tracker.summary_by_owner()
    if not by_owner.empty:
        fig = px.bar(by_owner, x="owner", y=["open_count", "in_progress_count", "closed_count"],
                     title="按负责人统计", barmode="stack")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(by_owner)

    st.divider()

    # 优先复盘清单
    st.subheader("优先复盘清单")
    priority_list = tracker.get_priority_review_list()
    if priority_list:
        priority_df = pd.DataFrame(priority_list)
        st.dataframe(priority_df)
    else:
        st.success("无高优先级项")

    st.divider()

    # 完整改善项列表
    st.subheader("改善项完整列表")
    st.dataframe(actions_df)

show()
