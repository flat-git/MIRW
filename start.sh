#!/bin/bash
# 一键启动前端 + 后端，并打开浏览器

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 启动后端
echo "Starting backend on http://localhost:8000 ..."
python -m uvicorn backend.app:app --reload &
BACKEND_PID=$!

# 启动前端
echo "Starting frontend on http://localhost:5173 ..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

# 等待前端就绪后打开浏览器
sleep 3
open http://localhost:5173

echo ""
echo "Both services started. Press Ctrl+C to stop."

# 捕获 Ctrl+C，清理两个进程
cleanup() {
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

wait
