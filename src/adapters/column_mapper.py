"""LLM 辅助列名映射。将未知列名映射到 canonical 字段。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict

from src.adapters.data_profiler import FileProfile, ColumnProfile
from src.reporting.llm_client import call_llm_flash


# canonical 字段定义（给 LLM 参考）
CANONICAL_FIELDS = {
    # 事件字段（优先）
    "event_id": "事件唯一 ID",
    "downtime_min": "停机分钟数（数值）",
    "raw_reason": "停机原因（简短文本分类）",
    "raw_note": "异常备注详情（长文本描述）",
    "machine_id": "设备编号/名称",
    "operator_id": "操作员姓名/编号",
    "shift": "班次（Day/Night/A/B/C 等）",
    "product_id": "产品编号/名称",
    "line_id": "产线/位置",
    "event_start": "停机开始时间",
    "event_end": "停机结束时间",
    # 批次字段（次要）
    "run_id": "生产批次 ID",
    "planned_time_min": "计划生产时间（分钟）",
    "runtime_min": "实际运行时间（分钟）",
    "target_output": "计划产出数量",
    "actual_output": "实际产出数量",
    "good_output": "良品数量",
    "scrap_output": "废品数量",
}


@dataclass
class ColumnMapping:
    source_column: str
    target_field: str | None
    confidence: float
    reasoning: str = ""


@dataclass
class MappingSuggestion:
    mappings: list[ColumnMapping] = field(default_factory=list)
    unmapped_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_adapter_mapping(self) -> dict[str, str]:
        """转为 GenericExcelAdapter 可用的映射：{target_field: source_column}。"""
        result = {}
        for m in self.mappings:
            if m.target_field and m.target_field in CANONICAL_FIELDS:
                result[m.target_field] = m.source_column
        return result


def suggest_mapping(profile: FileProfile) -> MappingSuggestion:
    """基于文件画像，用 LLM flash 建议列名映射。"""
    if not profile.sheets:
        return MappingSuggestion()

    # 取第一个 sheet 的列信息
    columns = profile.sheets[0].columns

    # 构造 LLM 输入
    columns_info = []
    for col in columns:
        columns_info.append({
            "name": col.name,
            "sample_values": col.sample_values[:3],
            "is_numeric": col.is_numeric,
            "is_datetime": col.is_datetime,
            "null_ratio": col.null_ratio,
        })

    prompt = _build_prompt(columns_info)

    try:
        response = call_llm_flash(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return _parse_response(response, columns)
    except Exception as e:
        # LLM 失败时返回空映射（用户手动选择）
        return MappingSuggestion(
            unmapped_columns=[c.name for c in columns],
        )


_SYSTEM_PROMPT = """你是制造业数据字段映射助手。
给定一组列名和样例值，将它们映射到标准字段。

只输出 JSON 数组，不要输出其他内容。
格式：[{"source_column": "原始列名", "target_field": "标准字段名或null", "confidence": 0.0-1.0}]
如果某列无法映射，target_field 设为 null。"""


def _build_prompt(columns_info: list[dict]) -> str:
    fields_desc = "\n".join(f"- {k}: {v}" for k, v in CANONICAL_FIELDS.items())
    cols_json = json.dumps(columns_info, ensure_ascii=False, indent=2)

    return f"""请将以下列映射到标准字段：

【标准字段】
{fields_desc}

【输入列信息】
{cols_json}

请输出 JSON 数组，每项格式：{{"source_column": "...", "target_field": "...", "confidence": 0.0-1.0}}
无法映射的列 target_field 设为 null。"""


def _parse_response(response: str, columns: list[ColumnProfile]) -> MappingSuggestion:
    """解析 LLM 响应。"""
    # 尝试提取 JSON
    response = response.strip()
    # 去掉 markdown 代码块
    if response.startswith("```"):
        response = re.sub(r"^```(?:json)?\s*", "", response)
        response = re.sub(r"\s*```$", "", response)

    try:
        items = json.loads(response)
    except json.JSONDecodeError:
        # 尝试找 JSON 数组
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            items = json.loads(match.group())
        else:
            return MappingSuggestion(unmapped_columns=[c.name for c in columns])

    mappings = []
    mapped_targets = set()

    for item in items:
        source = item.get("source_column", "")
        target = item.get("target_field")
        confidence = float(item.get("confidence", 0))

        # 验证 target 是否合法
        if target and target not in CANONICAL_FIELDS:
            target = None
            confidence = 0

        # 去重：同一 target 只保留最高 confidence
        if target and target in mapped_targets:
            # 找到已存在的同 target 映射
            existing = next((m for m in mappings if m.target_field == target), None)
            if existing and existing.confidence >= confidence:
                target = None  # 丢弃当前低置信度的
            elif existing:
                existing.target_field = None  # 丢弃旧的

        if target:
            mapped_targets.add(target)

        mappings.append(ColumnMapping(
            source_column=source,
            target_field=target,
            confidence=confidence,
            reasoning=item.get("reasoning", ""),
        ))

    unmapped = [c.name for c in columns if c.name not in {m.source_column for m in mappings}]

    return MappingSuggestion(mappings=mappings, unmapped_columns=unmapped)
