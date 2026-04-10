#!/bin/bash
# 启动股票技术分析 Web 应用（后端 + 前端）
# 用法: bash start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== 股票技术分析 Web 应用 ==="
echo ""

# 检查依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo "正在安装后端依赖..."
    pip install -e ".[web]" --break-system-packages -q
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "正在安装前端依赖..."
    cd frontend && npm install && cd ..
fi

# 启动后端
echo "启动后端 API (http://localhost:8000)..."
cd "$PROJECT_DIR"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 启动前端
echo "启动前端开发服务器 (http://localhost:5173)..."
cd "$PROJECT_DIR/frontend"
npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "✅ 启动完成!"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待任意进程退出
wait -n $BACKEND_PID $FRONTEND_PID 2>/dev/null

# 清理
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
