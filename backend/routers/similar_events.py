"""相似事件检索路由。"""

from fastapi import APIRouter, HTTPException
from backend.schemas.events import SearchRequest
from backend.services import search_service

router = APIRouter(prefix="/api/datasets/{dataset_id}/search", tags=["search"])


@router.post("")
def search_events(dataset_id: str, req: SearchRequest):
    try:
        results = search_service.search_similar_events(
            dataset_id, req.query, top_k=req.top_k, use_reranker=req.use_reranker,
        )
        return {"query": req.query, "results": results}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
