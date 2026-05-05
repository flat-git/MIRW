"""改善项复发判断。"""

from __future__ import annotations

from datetime import date

import pandas as pd


def detect_recurrence(
    actions_df: pd.DataFrame,
    events_df: pd.DataFrame,
    similarity_fn=None,
    threshold: float = 0.78,
) -> list[dict]:
    """检测关闭后复发的改善项。

    判断逻辑：
    如果某 action 已关闭（有 close_date），
    但 close_date 之后出现了相似的异常事件，
    则标记 recurrence_flag=true。

    Args:
        actions_df: 改善项 DataFrame
        events_df: 异常事件 DataFrame
        similarity_fn: 相似度判断函数 (note1, note2) -> float，可选
        threshold: 相似度阈值
    """
    recurrences = []

    if "status" not in actions_df.columns or "close_date" not in actions_df.columns:
        return recurrences

    closed_actions = actions_df[actions_df["status"] == "Closed"].copy()
    if closed_actions.empty:
        return recurrences

    for _, action in closed_actions.iterrows():
        close_date = action.get("close_date")
        if pd.isna(close_date):
            continue

        related_event_id = action.get("related_event_id")
        if not related_event_id:
            continue

        # 查找关联的原始事件
        if "event_id" in events_df.columns:
            original_events = events_df[events_df["event_id"] == related_event_id]
            if original_events.empty:
                continue
            original_note = original_events.iloc[0].get("raw_note", "")
            original_reason = original_events.iloc[0].get("raw_reason", "")
        else:
            continue

        # 查找 close_date 之后的事件
        if "event_start" in events_df.columns:
            future_events = events_df[
                pd.to_datetime(events_df["event_start"], errors="coerce") > pd.Timestamp(close_date)
            ]
        else:
            # 没有时间字段时，检查所有事件
            future_events = events_df[events_df["event_id"] != related_event_id]

        # 简单的关键词匹配复发检测（不依赖 embedding）
        for _, future in future_events.iterrows():
            future_reason = str(future.get("raw_reason", ""))
            future_note = str(future.get("raw_note", ""))

            is_similar = _keyword_similarity(
                f"{original_reason} {original_note}",
                f"{future_reason} {future_note}",
            )

            if is_similar >= threshold:
                recurrences.append({
                    "action_id": action.get("action_id", ""),
                    "related_event_id": related_event_id,
                    "recurred_event_id": future.get("event_id", ""),
                    "close_date": str(close_date),
                    "original_reason": original_reason,
                    "recurred_reason": future_reason,
                    "similarity": is_similar,
                })
                break  # 每个 action 只标记一次复发

    return recurrences


def _keyword_similarity(text1: str, text2: str) -> float:
    """基于关键词重叠的简单相似度。"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def apply_recurrence_flags(actions_df: pd.DataFrame, recurrences: list[dict]) -> pd.DataFrame:
    """将复发检测结果应用到 actions_df。"""
    result = actions_df.copy()

    recur_action_ids = {r["action_id"] for r in recurrences}
    result["recurrence_flag"] = result["action_id"].isin(recur_action_ids)

    return result
