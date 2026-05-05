"""GoMask Manufacturing Machine Downtime Logs 适配器。

数据来源：GoMask 公开制造停机日志，200 条停机事件。
特点：包含 cause_description、resolution_actions 等丰富文本字段，
      适合 LLM 异常备注标准化和改善项跟踪。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.adapters.base_adapter import BaseAdapter

# GoMask downtime_type → 标准损失类别映射
GOMASK_TYPE_MAP = {
    "mechanical": "Equipment",
    "electrical": "Equipment",
    "operator_error": "Operator",
    "scheduled_maintenance": "Changeover",
    "other": "Unknown",
}


class GoMaskDowntimeAdapter(BaseAdapter):
    """将 GoMask Manufacturing Downtime Logs 映射为统一模型。"""

    source_name = "gomask_manufacturing_downtime"

    def load_raw(self, path: str | Path) -> dict[str, pd.DataFrame]:
        """加载 GoMask CSV 文件。"""
        path = Path(path)
        if path.is_dir():
            csv_files = sorted(path.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(f"目录 {path} 中未找到 CSV 文件")
            path = csv_files[0]

        df = pd.read_csv(path, parse_dates=["downtime_start", "downtime_end", "report_date"])
        return {"main": df}

    def to_production_runs(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """按 location × day 聚合为 production_run。

        GoMask 数据是停机事件级别，没有显式的 production run。
        按 location + report_date 聚合作为虚拟生产批次。
        """
        df = raw["main"].copy()

        if "location" not in df.columns or "report_date" not in df.columns:
            return pd.DataFrame(columns=[
                "run_id", "source_dataset", "line_id", "downtime_min", "metadata",
            ])

        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        df["_date"] = df["report_date"].dt.date

        grouped = df.groupby(["location", "_date"]).agg(
            total_downtime_min=("duration_minutes", "sum"),
            event_count=("downtime_id", "count"),
            machine_count=("machine_id", "nunique"),
        ).reset_index()

        rows = []
        for _, row in grouped.iterrows():
            record = {
                "run_id": f"{self.source_name}_{row['location']}_{row['_date']}",
                "source_dataset": self.source_name,
                "line_id": _safe_str(row.get("location"), "Unknown"),
                "downtime_min": float(row["total_downtime_min"]),
                "metadata": {
                    "location": _safe_str(row.get("location"), "Unknown"),
                    "date": str(row["_date"]),
                    "event_count": int(row["event_count"]),
                    "machine_count": int(row["machine_count"]),
                },
            }
            rows.append(record)

        return pd.DataFrame(rows)

    def to_downtime_events(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """每行原始数据映射为一个 downtime_event。"""
        df = raw["main"].copy()

        rows = []
        for _, row in df.iterrows():
            dt_type = str(row.get("downtime_type", "other"))
            standard_cat = GOMASK_TYPE_MAP.get(dt_type, "Unknown")

            # 解析 production_impact 中的 units 数
            impact_text = str(row.get("production_impact", ""))
            impact_qty = _parse_impact_qty(impact_text)

            record = {
                "event_id": f"{self.source_name}_E{int(row['downtime_id']):04d}",
                "source_dataset": self.source_name,
                "machine_id": _safe_str(row.get("machine_id"), "Unknown"),
                "line_id": _safe_str(row.get("location"), "Unknown"),
                "event_start": row.get("downtime_start"),
                "event_end": row.get("downtime_end"),
                "downtime_min": float(row.get("duration_minutes", 0)),
                "raw_reason": _safe_str(row.get("downtime_type"), "other"),
                "standard_loss_category": standard_cat,
                "responsible_area": _safe_str(row.get("location")),
                "raw_note": _safe_str(row.get("cause_description"), ""),
                "evidence_text": _safe_str(row.get("cause_description"), ""),
                "metadata": {
                    "machine_name": row.get("machine_name"),
                    "location": row.get("location"),
                    "resolved_by": row.get("resolved_by"),
                    "resolution_actions": row.get("resolution_actions"),
                    "parts_replaced": row.get("parts_replaced"),
                    "scheduled_maintenance": row.get("scheduled_maintenance"),
                    "production_impact": impact_text,
                    "impact_qty": impact_qty,
                    "reported_by": row.get("reported_by"),
                    "report_date": str(row.get("report_date", "")),
                },
            }
            rows.append(record)

        return pd.DataFrame(rows)

    def detect_capability(self, runs: pd.DataFrame, events: pd.DataFrame) -> dict[str, bool]:
        """GoMask 数据的特殊能力检测。"""
        caps = super().detect_capability(runs, events)
        # GoMask 独有能力
        caps["repeated_issue_retrieval"] = "raw_note" in events.columns and events["raw_note"].notna().any()
        caps["resolution_tracking"] = "metadata" in events.columns
        caps["machine_analysis"] = "machine_id" in events.columns
        caps["location_analysis"] = "line_id" in events.columns
        caps["shift_analysis"] = False  # 无班次字段
        caps["operator_analysis"] = False  # operator 非标准化
        return caps


def _safe_str(value, default=None) -> str | None:
    """安全转字符串：NaN/None → default，避免 'nan' 字符串。"""
    if value is None:
        return default
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return default
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    if s.lower() == "nan" or s == "":
        return default
    return s


def _parse_impact_qty(text: str) -> int | None:
    """从 production_impact 文本中提取影响的 unit 数。"""
    import re
    if not text or text.lower() in ("no impact", "no measurable impact", "no units lost",
                                      "planned downtime, no impact", "lab test; no production affected",
                                      "minor delay, no units lost", "production halted for maintenance window",
                                      "all production suspended"):
        return 0
    # 匹配 "24 units" 或 "10 units"
    match = re.search(r"(\d+)\s*units?", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
