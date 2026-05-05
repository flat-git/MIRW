"""指标计算服务。调用 src/metrics 计算。"""

from __future__ import annotations

from backend.state import store
from src.metrics.efficiency import calculate_efficiency_summary
from src.metrics.pareto import top_loss_pareto
from src.metrics.downtime import (
    downtime_by_category, downtime_by_product,
    downtime_by_operator, downtime_by_machine,
)


def get_efficiency_summary(dataset_id: str) -> dict:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    runs_df = ds["runs_df"]
    events_df = ds["events_df"]

    eff = calculate_efficiency_summary(runs_df, events_df)
    return {
        "total_downtime_min": eff.get("total_downtime_min"),
        "total_planned_min": eff.get("total_planned_min"),
        "total_runtime_min": eff.get("total_runtime_min"),
        "downtime_ratio": eff.get("downtime_ratio"),
        "line_efficiency": eff.get("line_efficiency"),
        "total_runs": eff.get("total_runs", len(runs_df)),
        "total_events": len(events_df),
    }


def get_pareto(dataset_id: str, top_n: int = 10) -> list[dict]:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")
    pareto_df = top_loss_pareto(ds["events_df"], top_n=top_n)
    if pareto_df.empty:
        return []
    return pareto_df.reset_index().to_dict("records")


def get_downtime_by_group(dataset_id: str, group_by: str = "category") -> list[dict]:
    ds = store.get(dataset_id)
    if ds is None:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    events_df = ds["events_df"]
    fn_map = {
        "category": lambda: downtime_by_category(events_df),
        "product": lambda: downtime_by_product(events_df),
        "operator": lambda: downtime_by_operator(events_df),
        "machine": lambda: downtime_by_machine(events_df),
    }
    fn = fn_map.get(group_by)
    if fn is None:
        raise ValueError(f"不支持的分组: {group_by}")
    result_df = fn()
    if result_df.empty:
        return []
    return result_df.to_dict("records")
