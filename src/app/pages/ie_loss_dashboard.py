"""IE Loss Dashboard 页面：停机损失、Pareto、分组分析。"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.metrics.efficiency import calculate_efficiency_summary
from src.metrics.downtime import downtime_by_category, downtime_by_product, downtime_by_shift, downtime_by_operator
from src.metrics.pareto import top_loss_pareto
from src.metrics.loss_summary import generate_loss_summary


def show():
    st.header("IE 损失分析看板")

    events_df = _get_events_df()
    runs_df = _get_runs_df()

    if events_df is None:
        st.warning("请先在「数据源管理」页面加载数据。")
        return

    # 效率摘要
    if runs_df is not None:
        efficiency = calculate_efficiency_summary(runs_df, events_df)
    else:
        efficiency = {"total_downtime_min": events_df["downtime_min"].sum()}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总停机时间", f"{efficiency.get('total_downtime_min', 0):.0f} min")
    with col2:
        dt_ratio = efficiency.get("downtime_ratio")
        st.metric("停机比率", f"{dt_ratio:.1%}" if dt_ratio else "N/A")
    with col3:
        line_eff = efficiency.get("line_efficiency")
        st.metric("产线效率", f"{line_eff:.1%}" if line_eff else "N/A")
    with col4:
        st.metric("事件总数", f"{len(events_df)}")

    st.divider()

    # Top Loss Pareto
    st.subheader("Top Loss Pareto")
    pareto_df = top_loss_pareto(events_df)
    if not pareto_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pareto_df["category"],
            y=pareto_df["total_downtime_min"],
            name="停机时间 (min)",
            marker_color="steelblue",
        ))
        fig.add_trace(go.Scatter(
            x=pareto_df["category"],
            y=pareto_df["cumulative_ratio"],
            name="累计比率",
            yaxis="y2",
            marker_color="red",
            mode="lines+markers",
        ))
        fig.update_layout(
            yaxis=dict(title="停机时间 (min)"),
            yaxis2=dict(title="累计比率", overlaying="y", side="right", range=[0, 1]),
            xaxis_title="损失类别",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(pareto_df)
    else:
        st.info("无 Pareto 数据")

    st.divider()

    # 按产品分析
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("按产品分析")
        by_product = downtime_by_product(events_df)
        if not by_product.empty:
            fig = px.pie(by_product, names="product_id", values="total_downtime_min",
                         title="停机时间按产品分布")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(by_product)
        else:
            st.info("无产品维度数据")

    with col_right:
        st.subheader("按班次分析")
        by_shift = downtime_by_shift(events_df)
        if not by_shift.empty:
            fig = px.pie(by_shift, names="shift", values="total_downtime_min",
                         title="停机时间按班次分布")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(by_shift)
        else:
            st.info("无班次维度数据")

    # 按操作员分析
    st.subheader("按操作员分析")
    by_operator = downtime_by_operator(events_df)
    if not by_operator.empty:
        fig = px.bar(by_operator, x="operator_id", y="total_downtime_min",
                     title="停机时间按操作员分布")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(by_operator)
    else:
        st.info("无操作员维度数据")


def _get_events_df() -> pd.DataFrame | None:
    """从 session_state 获取当前选中的事件数据。"""
    for key in ["gomask_events", "synthetic_events", "maven_events", "kaggle_events", "generic_events"]:
        if key in st.session_state:
            return st.session_state[key]
    # 尝试用合成数据
    if "synthetic_notes" in st.session_state:
        return st.session_state["synthetic_notes"]
    return None


def _get_runs_df() -> pd.DataFrame | None:
    """从 session_state 获取当前选中的 runs 数据。"""
    for key in ["maven_runs", "kaggle_runs", "generic_runs"]:
        if key in st.session_state:
            return st.session_state[key]
    return None

show()
