"""Review Report 页面：报告生成与下载。"""

import streamlit as st
import pandas as pd

from src.reporting.report_checker import check_report
from src.actions.action_tracker import ActionTracker


def show():
    st.header("复盘报告生成")

    report_type = st.selectbox(
        "选择报告类型",
        ["IE 改善复盘周报", "质量 CAPA 草稿", "5Why 分析草稿"],
    )

    if report_type == "IE 改善复盘周报":
        _show_ie_report()
    elif report_type == "质量 CAPA 草稿":
        _show_capa_report()
    elif report_type == "5Why 分析草稿":
        _show_five_why()


def _show_ie_report():
    st.subheader("IE 改善复盘周报")

    period = st.text_input("报告周期", "2026-W18")

    events_df = _get_events_df()
    runs_df = _get_runs_df()

    if events_df is None:
        st.warning("请先在「数据源管理」页面加载数据。")
        return

    if st.button("生成 IE 周报"):
        with st.spinner("正在生成报告..."):
            try:
                from src.reporting.report_generator import generate_ie_weekly_report
                from src.metrics.loss_summary import _find_repeated_issues

                repeated = _find_repeated_issues(events_df)
                action_summary = None
                if "action_items" in st.session_state:
                    tracker = ActionTracker(st.session_state["action_items"])
                    action_summary = tracker.get_action_summary_for_report()

                result = generate_ie_weekly_report(
                    period=period,
                    runs_df=runs_df if runs_df is not None else pd.DataFrame(),
                    events_df=events_df,
                    repeated_issues=repeated,
                    action_summary=action_summary,
                )

                st.session_state["ie_report"] = result
                st.success("报告生成完成！")
            except Exception as e:
                st.error(f"生成失败：{e}")
                st.info("提示：LLM API 未配置时无法生成报告。请设置 .env 中的 LLM_API_KEY。")

    if "ie_report" in st.session_state:
        result = st.session_state["ie_report"]

        st.subheader("报告内容")
        st.markdown(result["report_markdown"])

        st.subheader("审核结果")
        check_result = result.get("check_result", {})
        for key, value in check_result.items():
            icon = "✅" if value else "❌"
            st.write(f"{icon} {key}: {value}")

        # 下载按钮
        st.download_button(
            "下载 Markdown",
            result["report_markdown"],
            file_name=f"ie_weekly_{period}.md",
            mime="text/markdown",
        )


def _show_capa_report():
    st.subheader("质量 CAPA 草稿")

    period = st.text_input("报告周期", "2026-W18")

    events_df = _get_events_df()
    runs_df = _get_runs_df()

    if events_df is None:
        st.warning("请先在「数据源管理」页面加载数据。")
        return

    if st.button("生成质量 CAPA 草稿"):
        with st.spinner("正在生成报告..."):
            try:
                from src.reporting.report_generator import generate_quality_capa_report
                from src.metrics.quality import quality_issue_pareto

                qpareto = quality_issue_pareto(events_df)
                quality_issues = qpareto.to_dict("records") if not qpareto.empty else []

                # 收集证据备注
                evidence = []
                if "raw_note" in events_df.columns:
                    evidence = events_df["raw_note"].dropna().head(5).tolist()

                result = generate_quality_capa_report(
                    period=period,
                    runs_df=runs_df if runs_df is not None else pd.DataFrame(),
                    events_df=events_df,
                    quality_issues=quality_issues,
                    evidence_notes=evidence,
                )

                st.session_state["capa_report"] = result
                st.success("报告生成完成！")
            except Exception as e:
                st.error(f"生成失败：{e}")

    if "capa_report" in st.session_state:
        result = st.session_state["capa_report"]

        st.subheader("报告内容")
        st.markdown(result["report_markdown"])

        st.subheader("审核结果")
        check_result = result.get("check_result", {})
        for key, value in check_result.items():
            icon = "✅" if value else "❌"
            st.write(f"{icon} {key}: {value}")

        st.download_button(
            "下载 Markdown",
            result["report_markdown"],
            file_name=f"quality_capa_{period}.md",
            mime="text/markdown",
        )


def _show_five_why():
    st.subheader("5Why 分析草稿")

    events_df = _get_events_df()

    if events_df is None:
        st.warning("请先在「数据源管理」页面加载数据。")
        return

    # 选择事件
    if "event_id" in events_df.columns and "raw_reason" in events_df.columns:
        event_options = events_df[["event_id", "raw_reason"]].drop_duplicates()
        selected = st.selectbox(
            "选择异常事件",
            event_options.apply(lambda r: f"{r['event_id']} - {r['raw_reason']}", axis=1),
        )
        selected_id = selected.split(" - ")[0] if selected else None
    else:
        selected_id = st.text_input("输入事件 ID")

    if selected_id and st.button("生成 5Why 草稿"):
        with st.spinner("正在生成..."):
            try:
                from src.reporting.five_why_generator import generate_five_why

                event_row = events_df[events_df["event_id"] == selected_id].iloc[0]

                result = generate_five_why(
                    event_id=selected_id,
                    raw_reason=str(event_row.get("raw_reason", "")),
                    raw_note=event_row.get("raw_note"),
                    downtime_min=float(event_row.get("downtime_min", 0)),
                )

                st.session_state["five_why_report"] = result
                st.success("5Why 草稿生成完成！")
            except Exception as e:
                st.error(f"生成失败：{e}")

    if "five_why_report" in st.session_state:
        result = st.session_state["five_why_report"]

        st.subheader("报告内容")
        st.markdown(result["report_markdown"])

        st.subheader("审核结果")
        check_result = result.get("check_result", {})
        for key, value in check_result.items():
            icon = "✅" if value else "❌"
            st.write(f"{icon} {key}: {value}")

        st.download_button(
            "下载 Markdown",
            result["report_markdown"],
            file_name=f"five_why_{selected_id}.md",
            mime="text/markdown",
        )


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
