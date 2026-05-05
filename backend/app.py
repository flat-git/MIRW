"""FastAPI 主入口。"""

import sys
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import datasets, metrics, similar_events, reports, actions

app = FastAPI(
    title="MIRW — 制造异常复盘工作台",
    description="Manufacturing Issue Review & Action Tracking Workbench API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(metrics.router)
app.include_router(similar_events.router)
app.include_router(reports.router)
app.include_router(actions.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "MIRW API"}
