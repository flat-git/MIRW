"""报告生成路由。"""

import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.schemas.reports import IeWeeklyRequest, CapaRequest, FiveWhyRequest
from backend.services import report_service
from backend.state import store

router = APIRouter(prefix="/api/datasets/{dataset_id}/reports", tags=["reports"])


@router.post("/ie-weekly")
def ie_weekly(dataset_id: str, req: IeWeeklyRequest):
    try:
        return report_service.generate_ie_weekly(dataset_id, req.period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capa")
def capa(dataset_id: str, req: CapaRequest):
    try:
        return report_service.generate_capa(dataset_id, req.period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/five-why")
def five_why(dataset_id: str, req: FiveWhyRequest):
    try:
        return report_service.generate_five_why_report(dataset_id, req.event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def report_history(dataset_id: str):
    """获取数据集的报告历史。"""
    return store.list_reports(dataset_id)


@router.get("/{report_id}/download")
def download_report(dataset_id: str, report_id: str):
    """下载单份报告为 markdown。"""
    report = store.get_report(dataset_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    markdown = report.get("report_markdown", "")
    filename = f"{report.get('report_type', 'report')}_{report.get('period', '')}_{report_id}.md"
    return StreamingResponse(
        io.BytesIO(markdown.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
