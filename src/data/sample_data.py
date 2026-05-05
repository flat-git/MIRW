"""读取和加载合成样例数据。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config.settings import settings


def load_synthetic_notes() -> pd.DataFrame:
    """加载合成异常备注数据。"""
    path = settings.data_dir / "sample" / "synthetic_abnormal_notes.csv"
    return pd.read_csv(path)


def load_synthetic_action_items() -> pd.DataFrame:
    """加载合成改善项数据。"""
    path = settings.data_dir / "sample" / "synthetic_action_items.csv"
    return pd.read_csv(path)


def load_generic_excel_mapping() -> dict:
    """加载通用 Excel 字段映射 YAML。"""
    import yaml

    path = settings.data_dir / "sample" / "generic_excel_mapping.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
