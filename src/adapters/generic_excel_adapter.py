"""通用 Excel 数据适配器。通过 YAML 字段映射读取任意 Excel 文件。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.adapters.base_adapter import BaseAdapter


class GenericExcelAdapter(BaseAdapter):
    """通过 YAML 映射读取用户上传的 Excel 文件。"""

    source_name = "generic_excel"

    def __init__(self, mapping_path: str | Path | None = None, mapping_dict: dict | None = None):
        if mapping_dict:
            self.mapping = mapping_dict
            self.source_name = mapping_dict.get("source_name", "generic_excel")
        elif mapping_path:
            with open(mapping_path, "r", encoding="utf-8") as f:
                self.mapping = yaml.safe_load(f)
            self.source_name = self.mapping.get("source_name", "generic_excel")
        else:
            self.mapping = {}

    def load_raw(self, path: str | Path) -> dict[str, pd.DataFrame]:
        """加载 Excel 文件。"""
        path = Path(path)
        if path.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        elif path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")
        return {"main": df}

    def to_production_runs(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """根据 YAML 映射转换为 production_run 表。"""
        df = raw["main"].copy()
        mapping = self.mapping.get("production_run", {})

        # 反转映射：source_col → target_col
        col_map = {v: k for k, v in mapping.items() if v in df.columns}

        result = df.rename(columns=col_map)
        result["source_dataset"] = self.source_name

        # 只保留映射到的列 + source_dataset
        target_cols = list(col_map.values()) + ["source_dataset"]
        # 以及 run_id（必需）
        if "run_id" not in target_cols:
            result["run_id"] = [f"{self.source_name}_RUN_{i + 1:04d}" for i in range(len(result))]
            target_cols.append("run_id")

        available_cols = [c for c in target_cols if c in result.columns]
        return result[available_cols]

    def to_downtime_events(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """根据 YAML 映射转换为 downtime_event 表。"""
        df = raw["main"].copy()
        mapping = self.mapping.get("downtime_event", {})

        col_map = {v: k for k, v in mapping.items() if v in df.columns}

        result = df.rename(columns=col_map)
        result["source_dataset"] = self.source_name

        target_cols = list(col_map.values()) + ["source_dataset"]
        if "event_id" not in target_cols:
            result["event_id"] = [f"{self.source_name}_E{i + 1:04d}" for i in range(len(result))]
            target_cols.append("event_id")
        if "raw_reason" not in target_cols:
            result["raw_reason"] = "Unknown"
            target_cols.append("raw_reason")
        if "downtime_min" not in target_cols:
            result["downtime_min"] = 0.0
            target_cols.append("downtime_min")

        available_cols = [c for c in target_cols if c in result.columns]
        return result[available_cols]
