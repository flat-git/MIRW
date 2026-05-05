"""指标路由。"""

from fastapi import APIRouter, HTTPException
from backend.services import metrics_service

router = APIRouter(prefix="/api/datasets/{dataset_id}/metrics", tags=["metrics"])


@router.get("/summary")
def get_summary(dataset_id: str):
    try:
        return metrics_service.get_efficiency_summary(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/pareto")
def get_pareto(dataset_id: str, top_n: int = 10):
    try:
        return metrics_service.get_pareto(dataset_id, top_n)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/downtime")
def get_downtime(dataset_id: str, group_by: str = "category"):
    try:
        return metrics_service.get_downtime_by_group(dataset_id, group_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
