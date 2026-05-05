"""Data Adapter 页面：数据源选择、字段映射、capability 检测。"""

import streamlit as st
import pandas as pd

from src.adapters.maven_downtime_adapter import MavenDowntimeAdapter
from src.adapters.gomask_downtime_adapter import GoMaskDowntimeAdapter
from src.adapters.kaggle_oee_adapter import KaggleOEEAdapter
from src.adapters.generic_excel_adapter import GenericExcelAdapter
from src.data.sample_data import load_synthetic_notes
from src.config.settings import settings


def show():
    st.header("数据源管理")

    source = st.selectbox(
        "选择数据源",
        ["Maven Manufacturing Downtime", "GoMask Manufacturing Downtime", "Kaggle OEE / Downtime", "通用 Excel", "合成数据 Demo"],
    )

    if source == "Maven Manufacturing Downtime":
        _show_maven()
    elif source == "GoMask Manufacturing Downtime":
        _show_gomask()
    elif source == "Kaggle OEE / Downtime":
        _show_kaggle()
    elif source == "通用 Excel":
        _show_generic()
    elif source == "合成数据 Demo":
        _show_synthetic()


def _show_maven():
    st.subheader("Maven Manufacturing Downtime")

    maven_dir = settings.data_dir / "raw" / "maven"
    st.info(f"数据目录：`{maven_dir}`")

    if st.button("加载 Maven 数据"):
        try:
            adapter = MavenDowntimeAdapter()
            raw = adapter.load_raw(maven_dir)
            st.session_state["maven_raw"] = raw
            st.session_state["maven_runs"] = adapter.to_production_runs(raw)
            st.session_state["maven_events"] = adapter.to_downtime_events(raw)

            validation = adapter.validate_output(
                st.session_state["maven_runs"],
                st.session_state["maven_events"],
            )
            st.session_state["maven_validation"] = validation

            st.success("Maven 数据加载成功！")
        except Exception as e:
            st.error(f"加载失败：{e}")

    if "maven_validation" in st.session_state:
        val = st.session_state["maven_validation"]

        st.subheader("Capability 检测")
        caps = val.get("capability", {})
        for key, value in caps.items():
            if key == "missing_fields":
                continue
            icon = "✅" if value else "❌"
            st.write(f"{icon} {key}")

        if caps.get("missing_fields"):
            st.warning(f"缺少字段：{', '.join(caps['missing_fields'])}")

        st.subheader("数据校验")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Production Runs**")
            runs_val = val.get("production_runs", {})
            st.write(f"通过: {'✅' if runs_val.get('passed') else '❌'}")
            if runs_val.get("errors"):
                for err in runs_val["errors"]:
                    st.error(err)
            st.json(runs_val.get("stats", {}))

        with col2:
            st.write("**Downtime Events**")
            events_val = val.get("downtime_events", {})
            st.write(f"通过: {'✅' if events_val.get('passed') else '❌'}")
            if events_val.get("errors"):
                for err in events_val["errors"]:
                    st.error(err)
            st.json(events_val.get("stats", {}))

    if "maven_runs" in st.session_state:
        st.subheader("Production Runs 预览")
        st.dataframe(st.session_state["maven_runs"].head(20))

    if "maven_events" in st.session_state:
        st.subheader("Downtime Events 预览")
        st.dataframe(st.session_state["maven_events"].head(20))


def _show_gomask():
    st.subheader("GoMask Manufacturing Downtime Logs")

    gomask_dir = settings.data_dir / "raw" / "gomask"
    st.info(f"数据目录：`{gomask_dir}`")

    st.markdown(
        """
        GoMask 停机日志数据，200 条停机事件，包含：
        - `cause_description` — 异常描述文本（支持 LLM 标准化和相似检索）
        - `resolution_actions` — 处理措施
        - `downtime_type` — 5 类停机原因（mechanical, electrical, operator_error, scheduled_maintenance, other）
        - `machine_id` / `location` — 设备和位置维度
        """
    )

    if st.button("加载 GoMask 数据"):
        try:
            adapter = GoMaskDowntimeAdapter()
            raw = adapter.load_raw(gomask_dir)
            st.session_state["gomask_raw"] = raw
            st.session_state["gomask_runs"] = adapter.to_production_runs(raw)
            st.session_state["gomask_events"] = adapter.to_downtime_events(raw)

            validation = adapter.validate_output(
                st.session_state["gomask_runs"],
                st.session_state["gomask_events"],
            )
            st.session_state["gomask_validation"] = validation

            st.success("GoMask 数据加载成功！")
        except Exception as e:
            st.error(f"加载失败：{e}")

    if "gomask_validation" in st.session_state:
        val = st.session_state["gomask_validation"]

        st.subheader("Capability 检测")
        caps = val.get("capability", {})
        for key, value in caps.items():
            if key == "missing_fields":
                continue
            icon = "✅" if value else "❌"
            st.write(f"{icon} {key}")

        st.subheader("数据校验")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Production Runs**")
            runs_val = val.get("production_runs", {})
            st.write(f"通过: {'✅' if runs_val.get('passed') else '❌'}")
            st.json(runs_val.get("stats", {}))
        with col2:
            st.write("**Downtime Events**")
            events_val = val.get("downtime_events", {})
            st.write(f"通过: {'✅' if events_val.get('passed') else '❌'}")
            st.json(events_val.get("stats", {}))

    if "gomask_runs" in st.session_state:
        st.subheader("Production Runs 预览")
        st.dataframe(st.session_state["gomask_runs"].head(20))

    if "gomask_events" in st.session_state:
        st.subheader("Downtime Events 预览")
        st.dataframe(st.session_state["gomask_events"].head(20))


def _show_kaggle():
    st.subheader("Kaggle OEE / Downtime")

    kaggle_dir = settings.data_dir / "raw" / "kaggle_oee"
    st.info(f"数据目录：`{kaggle_dir}`")

    if st.button("加载 Kaggle 数据"):
        try:
            adapter = KaggleOEEAdapter()
            raw = adapter.load_raw(kaggle_dir)
            st.session_state["kaggle_raw"] = raw
            st.session_state["kaggle_runs"] = adapter.to_production_runs(raw)
            st.session_state["kaggle_events"] = adapter.to_downtime_events(raw)

            validation = adapter.validate_output(
                st.session_state["kaggle_runs"],
                st.session_state["kaggle_events"],
            )
            st.session_state["kaggle_validation"] = validation

            st.success("Kaggle 数据加载成功！")
        except Exception as e:
            st.error(f"加载失败：{e}")

    if "kaggle_validation" in st.session_state:
        val = st.session_state["kaggle_validation"]

        st.subheader("Capability 检测")
        caps = val.get("capability", {})
        for key, value in caps.items():
            if key == "missing_fields":
                continue
            icon = "✅" if value else "❌"
            st.write(f"{icon} {key}")

    if "kaggle_runs" in st.session_state:
        st.subheader("Production Runs 预览")
        st.dataframe(st.session_state["kaggle_runs"].head(20))

    if "kaggle_events" in st.session_state:
        st.subheader("Downtime Events 预览")
        st.dataframe(st.session_state["kaggle_events"].head(20))


def _show_generic():
    st.subheader("通用 Excel 适配")

    uploaded_file = st.file_uploader("上传 Excel 或 CSV 文件", type=["xlsx", "xls", "csv"])
    mapping_file = st.file_uploader("上传 YAML 字段映射文件（可选）", type=["yaml", "yml"])

    if uploaded_file and st.button("加载数据"):
        try:
            mapping_dict = None
            if mapping_file:
                import yaml
                mapping_dict = yaml.safe_load(mapping_file)
            else:
                from src.data.sample_data import load_generic_excel_mapping
                mapping_dict = load_generic_excel_mapping()

            adapter = GenericExcelAdapter(mapping_dict=mapping_dict)

            # 保存上传文件到临时位置
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as f:
                f.write(uploaded_file.getbuffer())
                tmp_path = f.name

            raw = adapter.load_raw(tmp_path)
            runs = adapter.to_production_runs(raw)
            events = adapter.to_downtime_events(raw)

            st.session_state["generic_runs"] = runs
            st.session_state["generic_events"] = events

            st.success("通用 Excel 数据加载成功！")
        except Exception as e:
            st.error(f"加载失败：{e}")

    if "generic_runs" in st.session_state:
        st.subheader("Production Runs 预览")
        st.dataframe(st.session_state["generic_runs"].head(20))

    if "generic_events" in st.session_state:
        st.subheader("Downtime Events 预览")
        st.dataframe(st.session_state["generic_events"].head(20))


def _show_synthetic():
    st.subheader("合成数据 Demo")

    st.markdown(
        """
        合成数据包含 PCBA/SMT 制造现场的异常备注，用于演示：
        - 异常文本标准化
        - 相似事件检索
        - 报告生成流程

        > **注意**：这些是 demo synthetic notes，不是企业真实生产数据。
        """
    )

    if st.button("加载合成数据"):
        try:
            notes = load_synthetic_notes()
            st.session_state["synthetic_notes"] = notes
            st.success(f"加载成功，共 {len(notes)} 条记录")
        except Exception as e:
            st.error(f"加载失败：{e}")

    if "synthetic_notes" in st.session_state:
        st.dataframe(st.session_state["synthetic_notes"])

show()
