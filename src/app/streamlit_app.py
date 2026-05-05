"""制造现场异常复盘与改善闭环工作台 — Streamlit 主入口。"""

import streamlit as st

st.set_page_config(
    page_title="制造现场异常复盘工作台",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("制造现场异常复盘与改善闭环工作台")
st.caption("Manufacturing Issue Review & Action Tracking Workbench")

st.markdown(
    """
    ## 项目定位

    本工具面向 **IE 工程师 / 生产运营 / 质量工程师**，用于将生产停机、OEE 和异常记录
    从原始事件标准化为可复盘、可分类、可跟踪的改善材料。

    ### 核心流程

    ```
    OEE / 停机事件 / 生产异常记录
            ↓
    统一制造异常事件模型
            ↓
    损失计算与 Pareto 分析
            ↓
    异常文本标准化 + 相似事件检索
            ↓
    改善项闭环跟踪
            ↓
    IE 周报 / 质量 CAPA / 5Why 草稿生成
    ```

    ### 使用说明

    请使用左侧导航栏选择功能页面。
    """
)
