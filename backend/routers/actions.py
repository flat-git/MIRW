"""改善项路由。"""

from fastapi import APIRouter, HTTPException
from backend.services import action_service

router = APIRouter(prefix="/api/datasets/{dataset_id}/actions", tags=["actions"])


@router.get("")
def list_actions(dataset_id: str):
    try:
        return action_service.get_action_items(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary")
def action_summary(dataset_id: str):
    try:
        return action_service.get_action_summary(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
