"""数据源路由。"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from backend.schemas.dataset import DatasetLoadRequest
from backend.services import dataset_service
from backend.state import store

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("")
def list_datasets():
    return store.list_datasets()


@router.post("/load")
def load_dataset(req: DatasetLoadRequest):
    try:
        return dataset_service.load_dataset(req.source)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...), mapping: str | None = Form(None)):
    suffix = Path(file.filename or "").suffix
    if suffix.lower() not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        return dataset_service.upload_dataset(tmp_path, mapping)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str):
    try:
        return dataset_service.get_dataset_summary(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{dataset_id}/events")
def get_events(dataset_id: str, limit: int = 200):
    try:
        return dataset_service.get_events(dataset_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{dataset_id}/runs")
def get_runs(dataset_id: str, limit: int = 200):
    try:
        return dataset_service.get_runs(dataset_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
