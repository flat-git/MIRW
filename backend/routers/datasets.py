"""数据源路由。"""

import io
import tempfile
from pathlib import Path

import pandas as pd

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from backend.schemas.dataset import DatasetLoadRequest
from backend.schemas.import_schema import ImportRequest
from backend.services import dataset_service, import_service
from backend.services.report_service import generate_analysis_report
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


@router.get("/{dataset_id}/download/excel")
def download_excel(dataset_id: str):
    """下载清洗后的数据集为 .xlsx 文件。"""
    ds = store.get(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="数据集不存在")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        if len(ds["runs_df"]) > 0:
            _safe_df(ds["runs_df"]).to_excel(writer, sheet_name="Production Runs", index=False)
        _safe_df(ds["events_df"]).to_excel(writer, sheet_name="Downtime Events", index=False)
    buf.seek(0)

    filename = f"{ds['source']}_{dataset_id}_cleaned.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{dataset_id}/download/report")
def download_analysis_report(dataset_id: str):
    """下载数据分析报告为 markdown。"""
    try:
        md = generate_analysis_report(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    ds = store.get(dataset_id)
    filename = f"{ds['source']}_{dataset_id}_analysis.md"
    return StreamingResponse(
        io.BytesIO(md.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_df(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame 转为 Excel 安全格式（处理 NaN、datetime、dict 等）。"""
    import math
    result = df.copy()
    # 展开 metadata dict 列
    if "metadata" in result.columns:
        meta_df = result["metadata"].apply(lambda x: x if isinstance(x, dict) else {})
        meta_expanded = pd.DataFrame(meta_df.tolist())
        meta_expanded.columns = [f"meta_{c}" for c in meta_expanded.columns]
        result = pd.concat([result.drop(columns=["metadata"]), meta_expanded], axis=1)
    # NaN → 空字符串
    for col in result.columns:
        if result[col].dtype == object:
            result[col] = result[col].fillna("")
    return result
