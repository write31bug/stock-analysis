@echo off
chcp 65001 >nul 2>&1
title 股票技术分析 Web 应用

echo === 股票技术分析 Web 应用 ===
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查 Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: 安装后端依赖
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装后端依赖...
    pip install -e ".[web]" -q
)

:: 安装前端依赖
if not exist "frontend\node_modules" (
    echo 正在安装前端依赖...
    cd frontend
    call npm install
    cd ..
)

:: 提示数据库配置
echo.
echo ── 数据库配置 ──
echo 默认使用 MySQL (mysql+pymysql://root:123456@localhost:3306/stock_analysis)
echo 如需修改，编辑 .env 文件中的 DATABASE_URL
echo MySQL 连接失败时自动回退到 SQLite
echo.

:: 启动后端
echo 启动后端 API (http://localhost:8000)...
start "后端 API" cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端
echo 启动前端开发服务器 (http://localhost:5173)...
start "前端" cmd /c "cd frontend && npx vite --host 0.0.0.0 --port 5173"

echo.
echo ✅ 启动完成!
echo    前端: http://localhost:5173
echo    后端: http://localhost:8000
echo    API文档: http://localhost:8000/docs
echo.
echo 关闭弹出的两个命令行窗口即可停止服务
echo.
pause
