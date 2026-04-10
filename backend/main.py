"""FastAPI 入口"""

import logging
import os
import threading
from contextlib import asynccontextmanager

# 加载 .env 文件（必须在 database 导入之前）
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .log_handler import setup_db_logging
from .routers import alerts, analyze, export, history, log, portfolio, settings, watchlist
from .scheduler import get_scheduler_state, run_collect_once, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

_refresh_tasks: dict = {}
_refresh_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库 + 启动定时采集"""
    init_db()
    setup_db_logging()
    # 从环境变量读取采集间隔（分钟），默认 3 分钟
    interval_minutes = int(os.environ.get("COLLECT_INTERVAL", "3"))
    start_scheduler(interval=interval_minutes * 60)  # 转为秒
    logger.info("定时采集服务已启动（间隔 %d 分钟）", interval_minutes)
    yield
    stop_scheduler()


app = FastAPI(
    title="股票技术分析 API",
    description="基于 stock-analysis v1.8.0 的 REST API",
    version="1.8.0",
    lifespan=lifespan,
)

# CORS 配置（开发环境允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(analyze.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(log.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.8.0"}


@app.get("/api/scheduler/status")
async def scheduler_status():
    """获取定时采集服务状态"""
    return get_scheduler_state()


@app.post("/api/scheduler/refresh")
async def manual_refresh():
    """手动触发一次采集（后台执行，返回任务ID）"""
    import threading
    import uuid

    task_id = str(uuid.uuid4())[:8]

    def _run():
        try:
            result = run_collect_once()
            with _refresh_lock:
                _refresh_tasks[task_id] = {**result, "status": "completed"}
        except Exception as e:
            with _refresh_lock:
                _refresh_tasks[task_id] = {"status": "completed", "error": str(e), "collected": 0, "failed": 0}

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "running"}


@app.get("/api/scheduler/refresh/{task_id}")
async def get_refresh_status(task_id: str):
    """查询手动刷新进度"""
    with _refresh_lock:
        task = _refresh_tasks.get(task_id)
    if not task:
        return {"status": "running"}  # 还没写入就是还在跑
    return task
