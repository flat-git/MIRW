"""Maven Manufacturing Downtime 数据适配器。

适配 Maven Analytics 提供的真实 Excel 数据：
  4 个 sheet — Line productivity, Products, Downtime factors, Line downtime
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

from src.adapters.base_adapter import BaseAdapter


class MavenDowntimeAdapter(BaseAdapter):
    """将 Maven Manufacturing Downtime Excel 映射为统一模型。"""

    source_name = "maven_manufacturing_downtime"

    def load_raw(self, path: str | Path) -> dict[str, pd.DataFrame]:
        """加载 Maven Excel 文件（多 sheet）。"""
        path = Path(path)
        if path.is_dir():
            xlsx_files = sorted(path.glob("*.xlsx"))
            if not xlsx_files:
                raise FileNotFoundError(f"目录 {path} 中未找到 xlsx 文件")
            path = xlsx_files[0]

        xls = pd.ExcelFile(path)
        raw = {}
        for sheet in xls.sheet_names:
            raw[sheet] = pd.read_excel(xls, sheet_name=sheet)
        return raw

    def to_production_runs(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将 Line productivity sheet 映射为 production_run 表。

        每行一个批次，附带产品信息和计算的运行时间。
        """
        df_prod = raw["Line productivity"].copy()
        df_products = raw.get("Products", pd.DataFrame())

        # 合并产品信息
        if not df_products.empty and "Product" in df_products.columns:
            df = df_prod.merge(df_products, on="Product", how="left")
        else:
            df = df_prod

        # 计算运行时间（分钟）
        df["runtime_min"] = df.apply(self._calc_runtime_minutes, axis=1)

        # 合并停机数据计算总停机时间
        dt_totals = self._calc_downtime_totals(raw)
        df["downtime_min"] = df["Batch"].map(dt_totals).fillna(0.0)

        # 计算计划时间 = 运行时间 + 停机时间
        df["planned_time_min"] = df["runtime_min"] + df["downtime_min"]

        # 构造 production_run 表
        rows = []
        for _, row in df.iterrows():
            record = {
                "run_id": f"{self.source_name}_{int(row['Batch'])}",
                "source_dataset": self.source_name,
                "product_id": str(row["Product"]),
                "operator_id": str(row["Operator"]),
                "planned_time_min": float(row["planned_time_min"]),
                "runtime_min": float(row["runtime_min"]),
                "downtime_min": float(row["downtime_min"]),
                "metadata": {
                    "batch": int(row["Batch"]),
                    "date": str(row["Date"].date()) if pd.notna(row["Date"]) else None,
                    "start_time": str(row.get("Start Time", "")),
                    "end_time": str(row.get("End Time", "")),
                    "flavor": row.get("Flavor"),
                    "size": row.get("Size"),
                    "min_batch_time": row.get("Min batch time"),
                },
            }
            rows.append(record)

        return pd.DataFrame(rows)

    def to_downtime_events(self, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将 Line downtime sheet 解析为 downtime_event 表。

        Line downtime 是宽表（Batch × Factor code），需要 unpivot。
        """
        df_dt = raw["Line downtime"].copy()
        df_factors = raw.get("Downtime factors", pd.DataFrame())
        df_prod = raw["Line productivity"].copy()

        # 第 0 行是 header: ["Batch", 1, 2, 3, ..., 12]
        # 从第 1 行开始是数据
        # 重命名列
        factor_cols = [c for c in df_dt.columns if c != "Unnamed: 0"]
        # 构造列名映射：Downtime factor → 1, Unnamed: 2 → 2, ...
        col_rename = {}
        for col in factor_cols:
            if col == "Downtime factor":
                col_rename[col] = 1
            elif col.startswith("Unnamed:"):
                # 提取数字
                try:
                    num = int(float(df_dt.iloc[0][col]))
                    col_rename[col] = num
                except (ValueError, TypeError):
                    pass

        # 取实际数据（跳过第 0 行 header）
        df_data = df_dt.iloc[1:].copy()
        df_data = df_data.rename(columns={"Unnamed: 0": "Batch"})
        df_data = df_data.rename(columns=col_rename)

        # 确保 Batch 为整数
        df_data["Batch"] = pd.to_numeric(df_data["Batch"], errors="coerce")
        df_data = df_data.dropna(subset=["Batch"])
        df_data["Batch"] = df_data["Batch"].astype(int)

        # Unpivot: 宽表 → 长表
        factor_ids = [c for c in df_data.columns if c != "Batch" and isinstance(c, (int, float))]
        df_long = df_data.melt(id_vars=["Batch"], value_vars=factor_ids,
                               var_name="factor_id", value_name="downtime_min")
        df_long = df_long.dropna(subset=["downtime_min"])

        # 合并停机原因描述
        if not df_factors.empty and "Factor" in df_factors.columns:
            df_factors["Factor"] = pd.to_numeric(df_factors["Factor"], errors="coerce")
            df_long["factor_id"] = pd.to_numeric(df_long["factor_id"], errors="coerce")
            df_long = df_long.merge(
                df_factors[["Factor", "Description", "Operator Error"]],
                left_on="factor_id", right_on="Factor", how="left",
            )
        else:
            df_long["Description"] = "Unknown"
            df_long["Operator Error"] = "Unknown"

        # 合并批次信息
        if not df_prod.empty:
            df_long = df_long.merge(
                df_prod[["Batch", "Product", "Operator", "Date"]],
                on="Batch", how="left",
            )

        # 构造 downtime_event 表
        rows = []
        for idx, row in df_long.iterrows():
            event_id = f"{self.source_name}_B{int(row['Batch'])}_F{int(row['factor_id'])}"
            record = {
                "event_id": event_id,
                "run_id": f"{self.source_name}_{int(row['Batch'])}",
                "source_dataset": self.source_name,
                "downtime_min": float(row["downtime_min"]),
                "raw_reason": str(row.get("Description", "Unknown")),
                "product_id": str(row.get("Product", "")) if pd.notna(row.get("Product")) else None,
                "operator_id": str(row.get("Operator", "")) if pd.notna(row.get("Operator")) else None,
                "metadata": {
                    "batch": int(row["Batch"]),
                    "factor_id": int(row["factor_id"]),
                    "operator_error": row.get("Operator Error"),
                    "date": str(row["Date"].date()) if pd.notna(row.get("Date")) else None,
                },
            }
            rows.append(record)

        return pd.DataFrame(rows)

    def _calc_runtime_minutes(self, row) -> float:
        """从 Start Time / End Time 计算运行时间（分钟）。"""
        try:
            start = pd.to_datetime(row["Start Time"], format="%H:%M:%S")
            end = pd.to_datetime(row["End Time"], format="%H:%M:%S")
            delta = (end - start).total_seconds() / 60
            return max(delta, 0)
        except Exception:
            return 0.0

    def _calc_downtime_totals(self, raw: dict[str, pd.DataFrame]) -> dict[int, float]:
        """计算每个 Batch 的总停机分钟数。"""
        df_dt = raw["Line downtime"].copy()
        df_data = df_dt.iloc[1:].copy()
        df_data = df_data.rename(columns={"Unnamed: 0": "Batch"})
        df_data["Batch"] = pd.to_numeric(df_data["Batch"], errors="coerce")
        df_data = df_data.dropna(subset=["Batch"])
        df_data["Batch"] = df_data["Batch"].astype(int)

        # 数值列求和
        num_cols = [c for c in df_dt.columns if c not in ("Unnamed: 0", "Downtime factor")]
        df_data[num_cols] = df_data[num_cols].apply(pd.to_numeric, errors="coerce")
        totals = df_data[num_cols].sum(axis=1)
        return dict(zip(df_data["Batch"], totals))
