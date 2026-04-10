"""系统日志接口"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SystemLog

router = APIRouter(tags=["logs"])


@router.get("/logs")
async def get_logs(
    level: Optional[str] = Query(None, description="日志级别: INFO/WARNING/ERROR"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """获取系统日志列表"""
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level.upper())
    items = query.order_by(SystemLog.created_at.desc()).offset(offset).limit(limit).all()
    return [item.to_dict() for item in items]


@router.delete("/logs")
async def clear_logs(db: Session = Depends(get_db)):
    """清空日志"""
    count = db.query(SystemLog).count()
    db.query(SystemLog).delete()
    db.commit()
    return {"message": f"已清空 {count} 条日志"}
