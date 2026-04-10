"""系统设置接口"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..scheduler import get_scheduler_state, start_scheduler, stop_scheduler

router = APIRouter(tags=["settings"])


class IntervalRequest(BaseModel):
    interval_minutes: int = Field(..., ge=1, le=1440, description="采集间隔（分钟），1-1440")


@router.get("/settings/interval")
async def get_interval():
    """获取当前采集间隔（分钟）"""
    state = get_scheduler_state()
    interval_seconds = state.get("interval", 180)
    return {
        "interval_minutes": int(interval_seconds) // 60,
        "running": state.get("running", False),
    }


@router.put("/settings/interval")
async def set_interval(req: IntervalRequest):
    """动态修改采集间隔（分钟）"""
    old_thread = stop_scheduler()
    if old_thread and old_thread.is_alive():
        old_thread.join(timeout=5)
    start_scheduler(interval=req.interval_minutes * 60)
    return {
        "message": f"采集间隔已修改为 {req.interval_minutes} 分钟",
        "success": True,
        "interval_minutes": req.interval_minutes,
    }
