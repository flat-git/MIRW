"""报告生成路由。"""

from fastapi import APIRouter, HTTPException
from backend.schemas.reports import IeWeeklyRequest, CapaRequest, FiveWhyRequest
from backend.services import report_service

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
