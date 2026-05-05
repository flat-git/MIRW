"""LLM 报告 Prompt 模板。"""

import json

# ========================================
# IE 周报模板
# ========================================

IE_WEEKLY_SYSTEM_PROMPT = """你是 IE 改善复盘报告助手。
你只能基于输入 JSON 生成报告。
所有数值必须原样引用，不得自行计算。
所有根因必须写成"候选根因"。
所有改善建议必须写成"建议 / 待人工确认"。
不得编造不存在的产线、设备、人员、物料或批次。
报告必须包含"待人工确认事项"。
输出 Markdown 格式。"""

IE_WEEKLY_REPORT_STRUCTURE = """请按照以下结构生成 IE 周报：

# IE 改善复盘周报 — {period}

## 1. 本周期生产效率概况
（引用 total_downtime_min、line_efficiency、downtime_ratio 等数值）

## 2. Top Loss 分析
（按 Pareto 排列，列出前 5 类损失及其占比）

## 3. 重复异常分析
（列出重复发生的问题、次数、累计影响时间）

## 4. 改善项状态
（Open / In Progress / Closed 数量，overdue 项，closed 后复发项）

## 5. 下周复盘重点
（基于 Top Loss 和重复异常，建议下周重点关注方向）

## 6. 待人工确认事项
（列出所有需要人工确认的内容）"""


# ========================================
# 质量 CAPA 模板
# ========================================

CAPA_SYSTEM_PROMPT = """你是质量异常复盘与 CAPA 草稿助手。
你只能基于输入 JSON 生成 5Why / CAPA 草稿。
不得把候选原因写成确定原因。
不得编造不存在的工艺参数、设备编号、人员、供应商、物料批次。
必须保留原始异常备注作为证据。
必须标注"待质量工程师确认"。
输出 Markdown 格式。"""

CAPA_REPORT_STRUCTURE = """请按照以下结构生成质量 CAPA 草稿：

# 质量异常复盘与 CAPA 草稿 — {period}

## 1. 质量异常概况
（引用 quality_related_downtime_min、scrap_rate 等数值）

## 2. Top Quality Issues
（按影响时间排列质量异常类别）

## 3. 重复异常与复发情况
（列出重复发生的质量问题）

## 4. 初步 5Why 草稿
（为 Top 1-2 质量问题提供 5Why 分析草稿，标注候选原因）

## 5. CAPA 草稿
（为 Top 质量问题提供 CAPA 草稿，包含临时对策和长期对策建议）

## 6. 待质量工程师确认事项
（列出所有需要质量工程师确认的内容）"""


# ========================================
# 5Why 模板
# ========================================

FIVE_WHY_SYSTEM_PROMPT = """你是 5Why 分析草稿助手。
你只能基于输入 JSON 生成 5Why 分析草稿。
不得把候选原因写成确定原因。
不得编造不存在的设备编号、人员、物料批次、工艺参数。
每层 Why 必须标注"候选原因 / 待确认"。
必须保留原始异常备注作为证据。
输出 Markdown 格式。"""


def build_ie_weekly_prompt(data: dict) -> list[dict]:
    """构建 IE 周报 prompt。"""
    return [
        {"role": "system", "content": IE_WEEKLY_SYSTEM_PROMPT},
        {"role": "user", "content": IE_WEEKLY_REPORT_STRUCTURE.format(period=data.get("period", "N/A"))},
        {"role": "user", "content": f"以下是本周期的数据，请基于此生成报告：\n\n```json\n{_to_json(data)}\n```"},
    ]


def build_capa_prompt(data: dict) -> list[dict]:
    """构建质量 CAPA prompt。"""
    return [
        {"role": "system", "content": CAPA_SYSTEM_PROMPT},
        {"role": "user", "content": CAPA_REPORT_STRUCTURE.format(period=data.get("period", "N/A"))},
        {"role": "user", "content": f"以下是本周期的数据，请基于此生成报告：\n\n```json\n{_to_json(data)}\n```"},
    ]


def build_five_why_prompt(issue_data: dict) -> list[dict]:
    """构建 5Why 分析 prompt。"""
    prompt = f"""请为以下异常事件生成 5Why 分析草稿：

```json
{_to_json(issue_data)}
```

格式要求：
# 5Why 分析草稿

## 异常事件
（描述异常现象和影响）

## 5Why 分析
- Why 1: ... → 候选原因 / 待确认
- Why 2: ... → 候选原因 / 待确认
- Why 3: ... → 候选原因 / 待确认
- Why 4: ... → 候选原因 / 待确认
- Why 5: ... → 候选原因 / 待确认

## 初步对策建议
（临时对策和长期对策建议）

## 待人工确认事项
"""

    return [
        {"role": "system", "content": FIVE_WHY_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def _to_json(data: dict) -> str:
    """将 dict 转为 JSON 字符串。"""
    return json.dumps(data, ensure_ascii=False, indent=2)
