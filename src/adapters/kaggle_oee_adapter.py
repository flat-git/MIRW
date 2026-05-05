"""Kaggle OEE / Downtime 数据适配器。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.adapters.base_adapter import BaseAdapter


class KaggleOEEAdapter(BaseAdapter):
    """将 Kaggle OEE / Downtime 数据映射为统一模型。"""

    source_name = "kaggle_oee_downtime"

    def load_raw(self, path: str | Path) -> dict[str, pd.DataFrame]:
        """加载 Kaggle OEE 原始 CSV 文件。"""
        path = Path(path)
        if path.is_dir():
            csv_files = sorted(path.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(f"目录 {path} 中未找到 CSV 文件")
            # 尝试找到主数据文件
            main_file = None
            for f in csv_files:
                name_lower = f.stem.lower()
                if any(kw in name_lower for kw in ["oee", "downtime", "manufacturing", "production"]):
                    main_file = f
                    break
            if main_file is None:
                main_file = csv_files[0]
            df = pd.read_csv(main_file)
        else:
            df = pd.read_csv(path)
        return {"main": df}

    def to_production_runs(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """映射为 production_run 表。"""
        df = raw["main"].copy()

        # 自动检测列名
        machine_col = self._find_column(df, ["Machine_ID", "Machine", "machine_id", "Equipment", "MachineID"])
        shift_col = self._find_column(df, ["Shift", "shift", "Shift_ID"])
        date_col = self._find_column(df, ["Date", "date", "Production_Date"])

        planned_col = self._find_column(df, ["Planned_Production_Time", "Planned Time", "planned_time_min", "PlannedProductionTime"])
        run_col = self._find_column(df, ["Run_Time", "Runtime", "runtime_min", "Operating_Time"])
        downtime_col = self._find_column(df, ["Downtime", "Downtime_Minutes", "downtime_min", "Total_Downtime"])

        target_col = self._find_column(df, ["Ideal_Cycle_Time", "Target_Output", "target_output"])
        actual_col = self._find_column(df, ["Total_Count", "Actual_Output", "actual_output", "Units_Produced"])
        good_col = self._find_column(df, ["Good_Count", "Good_Output", "good_output", "Good_Units"])
        scrap_col = self._find_column(df, ["Defect_Count", "Scrap", "scrap_output", "Defective_Units", "Scrap_Count"])

        rows = []
        for idx, row in df.iterrows():
            record = {
                "run_id": f"{self.source_name}_RUN_{idx + 1:04d}",
                "source_dataset": self.source_name,
            }

            if machine_col:
                record["machine_id"] = str(row[machine_col]) if pd.notna(row.get(machine_col)) else None
            if shift_col:
                record["shift"] = str(row[shift_col]) if pd.notna(row.get(shift_col)) else None

            for src, dst in [
                (planned_col, "planned_time_min"),
                (run_col, "runtime_min"),
                (downtime_col, "downtime_min"),
                (target_col, "target_output"),
                (actual_col, "actual_output"),
                (good_col, "good_output"),
                (scrap_col, "scrap_output"),
            ]:
                if src and pd.notna(row.get(src)):
                    record[dst] = float(row[src])

            rows.append(record)

        return pd.DataFrame(rows)

    def to_downtime_events(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """映射为 downtime_event 表。

        Kaggle OEE 数据通常是聚合级别（每行一个 shift/day 的汇总），
        如果没有明细停机事件，则每行视为一个聚合停机事件。
        """
        df = raw["main"].copy()

        machine_col = self._find_column(df, ["Machine_ID", "Machine", "machine_id", "Equipment"])
        shift_col = self._find_column(df, ["Shift", "shift", "Shift_ID"])
        downtime_col = self._find_column(df, ["Downtime", "Downtime_Minutes", "downtime_min", "Total_Downtime"])
        cause_col = self._find_column(df, ["Downtime_Reason", "Downtime_Cause", "Cause", "reason", "Downtime_Factor"])

        rows = []
        for idx, row in df.iterrows():
            downtime = 0.0
            if downtime_col and pd.notna(row.get(downtime_col)):
                downtime = float(row[downtime_col])

            reason = "Aggregated downtime"
            if cause_col and pd.notna(row.get(cause_col)):
                reason = str(row[cause_col])

            record = {
                "event_id": f"{self.source_name}_E{idx + 1:04d}",
                "source_dataset": self.source_name,
                "downtime_min": downtime,
                "raw_reason": reason,
            }

            if machine_col:
                record["machine_id"] = str(row[machine_col]) if pd.notna(row.get(machine_col)) else None
            if shift_col:
                record["shift"] = str(row[shift_col]) if pd.notna(row.get(shift_col)) else None

            rows.append(record)

        return pd.DataFrame(rows)

    def _find_column(self, df: pd.DataFrame, candidates: list[str]) -> str | None:
        """从候选列名中找到实际存在的列。"""
        for name in candidates:
            if name in df.columns:
                return name
        return None
