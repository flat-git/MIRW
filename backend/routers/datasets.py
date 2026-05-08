"""数据源路由。"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from backend.schemas.dataset import DatasetLoadRequest
from backend.schemas.import_schema import ImportRequest
from backend.services import dataset_service, import_service
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


@router.post("/analyze")
async def analyze_dataset(file: UploadFile = File(...)):
    """Step 1: 分析上传文件，返回列画像 + LLM 映射建议。"""
    suffix = Path(file.filename or "").suffix
    if suffix.lower() not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        return import_service.analyze_file(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import")
def import_dataset(req: ImportRequest):
    """Step 2: 用户确认映射后执行导入。"""
    try:
        mappings = [{"source_column": m.source_column, "target_field": m.target_field}
                    for m in req.confirmed_mappings]
        return import_service.execute_import(
            analysis_id=req.analysis_id,
            confirmed_mappings=mappings,
            deduplicate=req.deduplicate,
            normalize_nulls=req.normalize_nulls,
            coerce_types=req.coerce_types,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
