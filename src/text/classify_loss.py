"""基于关键词的损失分类辅助。在 LLM 不可用时作为 fallback。"""

from __future__ import annotations


# 关键词到标准类别的映射
KEYWORD_CATEGORY_MAP = {
    "Equipment": [
        "equipment", "failure", "breakdown", "repair", "malfunction",
        "设备", "故障", "维修", "马达", "链条", "风扇", "治具",
    ],
    "Material": [
        "material", "shortage", "supply", "incoming", "material issue",
        "来料", "物料", "缺料", "混料", "锡膏", "标签",
    ],
    "Quality": [
        "quality", "defect", "scrap", "rework", "inspection", "aoi",
        "质量", "虚焊", "桥连", "返修", "检出", "误判",
    ],
    "Changeover": [
        "changeover", "setup", "recipe", "换线", "换型", "调用", "程序版本",
    ],
    "Process": [
        "process", "parameter", "adjustment", "工艺", "参数", "温度",
    ],
    "Planning": [
        "planning", "schedule", "计划", "排产",
    ],
    "Operator": [
        "operator", "waiting", "delay", "人员", "等待",
    ],
    "Inspection": [
        "inspection", "first article", "首件", "确认", "复判", "校准",
    ],
}


def classify_by_keyword(raw_reason: str, raw_note: str | None = None) -> dict:
    """基于关键词进行粗分类。LLM 不可用时的 fallback。"""
    text = f"{raw_reason} {raw_note or ''}".lower()

    scores: dict[str, int] = {}
    for category, keywords in KEYWORD_CATEGORY_MAP.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[category] = score

    if not scores:
        return {
            "standard_loss_category": "Unknown",
            "confidence": 0.0,
            "needs_review": True,
        }

    best_category = max(scores, key=scores.get)
    max_score = scores[best_category]
    # 简单置信度：匹配关键词数 / 3，上限 0.9
    confidence = min(0.9, max_score / 3)

    return {
        "standard_loss_category": best_category,
        "confidence": round(confidence, 2),
        "needs_review": confidence < 0.65,
    }
