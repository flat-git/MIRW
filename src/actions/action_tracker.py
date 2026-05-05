"""改善项闭环跟踪。"""

from __future__ import annotations

from datetime import date

import pandas as pd


class ActionTracker:
    """改善项跟踪器。"""

    def __init__(self, actions_df: pd.DataFrame):
        self.actions = actions_df.copy()
        # 确保日期列类型正确
        for col in ["due_date", "close_date"]:
            if col in self.actions.columns:
                self.actions[col] = pd.to_datetime(self.actions[col], errors="coerce").dt.date

    def summary_by_status(self) -> dict:
        """按状态汇总。"""
        if "status" not in self.actions.columns:
            return {"Open": 0, "In Progress": 0, "Closed": 0}

        counts = self.actions["status"].value_counts().to_dict()
        return {
            "Open": counts.get("Open", 0),
            "In Progress": counts.get("In Progress", 0),
            "Closed": counts.get("Closed", 0),
            "total": len(self.actions),
        }

    def get_overdue(self, reference_date: date | None = None) -> pd.DataFrame:
        """获取超期改善项。"""
        if reference_date is None:
            reference_date = date.today()

        if "due_date" not in self.actions.columns:
            return pd.DataFrame()

        # 超期 = 未关闭 且 due_date < 参考日期
        mask = (
            (self.actions["status"] != "Closed")
            & self.actions["due_date"].notna()
            & (self.actions["due_date"] < reference_date)
        )
        return self.actions[mask].copy()

    def get_recurred(self) -> pd.DataFrame:
        """获取关闭后复发的改善项。"""
        if "recurrence_flag" not in self.actions.columns:
            return pd.DataFrame()
        return self.actions[self.actions["recurrence_flag"] == True].copy()

    def summary_by_owner(self) -> pd.DataFrame:
        """按负责人汇总。"""
        if "owner" not in self.actions.columns:
            return pd.DataFrame()

        grouped = self.actions.groupby("owner").agg(
            total=("action_id", "count"),
            open_count=("status", lambda x: (x == "Open").sum()),
            in_progress_count=("status", lambda x: (x == "In Progress").sum()),
            closed_count=("status", lambda x: (x == "Closed").sum()),
        ).reset_index()

        return grouped.sort_values("total", ascending=False)

    def summary_by_issue_type(self) -> pd.DataFrame:
        """按关联问题类型汇总。"""
        if "problem" not in self.actions.columns:
            return pd.DataFrame()

        # 使用 problem 字段进行简单分类
        grouped = self.actions.groupby("problem").agg(
            count=("action_id", "count"),
            open_count=("status", lambda x: (x == "Open").sum()),
        ).reset_index()

        return grouped.sort_values("count", ascending=False)

    def get_priority_review_list(self, reference_date: date | None = None) -> list[dict]:
        """生成优先复盘清单。"""
        items = []

        # 1. 超期项
        overdue = self.get_overdue(reference_date)
        for _, row in overdue.iterrows():
            items.append({
                "priority": "高",
                "reason": "超期",
                "action_id": row.get("action_id", ""),
                "problem": row.get("problem", ""),
                "owner": row.get("owner", ""),
                "due_date": str(row.get("due_date", "")),
            })

        # 2. 关闭后复发项
        recurred = self.get_recurred()
        for _, row in recurred.iterrows():
            items.append({
                "priority": "高",
                "reason": "关闭后复发",
                "action_id": row.get("action_id", ""),
                "problem": row.get("problem", ""),
                "owner": row.get("owner", ""),
            })

        # 3. 长期 Open 项（无 due_date 或超过 14 天未关闭）
        if "status" in self.actions.columns and "due_date" in self.actions.columns:
            long_open = self.actions[
                (self.actions["status"] == "Open")
                & self.actions["due_date"].isna()
            ]
            for _, row in long_open.iterrows():
                items.append({
                    "priority": "中",
                    "reason": "无截止日期",
                    "action_id": row.get("action_id", ""),
                    "problem": row.get("problem", ""),
                    "owner": row.get("owner", ""),
                })

        return items

    def get_action_summary_for_report(self, reference_date: date | None = None) -> dict:
        """生成用于 IE 周报输入的改善项摘要。"""
        status_summary = self.summary_by_status()
        overdue = self.get_overdue(reference_date)
        recurred = self.get_recurred()

        return {
            "open": status_summary.get("Open", 0),
            "in_progress": status_summary.get("In Progress", 0),
            "closed": status_summary.get("Closed", 0),
            "overdue": len(overdue),
            "closed_recurred": len(recurred),
        }
