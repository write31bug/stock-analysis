"""历史记录接口"""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AnalysisRecord
from ..schemas import (
    HistoryListResponse,
)
from ..schemas import HistoryRecord as HistoryRecordSchema
from ..schemas import (
    SaveHistoryRequest,
    ScoreTrendPoint,
)

router = APIRouter(tags=["history"])


@router.post("/history")
async def save_history(req: SaveHistoryRequest, db: Session = Depends(get_db)):
    """保存分析记录"""
    si = req.stock_info
    an = req.analysis
    ti = req.technical_indicators

    record = AnalysisRecord(
        code=si.get("code", ""),
        name=si.get("name", ""),
        market=si.get("market", ""),
        asset_type=si.get("asset_type", ""),
        score=an.get("score"),
        trend=an.get("trend"),
        recommendation=an.get("recommendation"),
        current_price=si.get("current_price"),
        change_pct=si.get("change_pct"),
        summary=an.get("summary"),
        indicators_json=json.dumps(ti, ensure_ascii=False, default=str),
        analysis_time=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "保存成功", "id": record.id}


@router.get("/history", response_model=HistoryListResponse)
async def get_history(
    code: str = Query(None),
    trend: str = Query(None),
    start: str = Query(None),
    end: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页查询历史记录"""
    query = db.query(AnalysisRecord)

    if code:
        query = query.filter(AnalysisRecord.code == code)
    if trend:
        query = query.filter(AnalysisRecord.trend == trend)
    if start:
        query = query.filter(AnalysisRecord.analysis_time >= start)
    if end:
        query = query.filter(AnalysisRecord.analysis_time <= end + " 23:59:59")

    total = query.count()
    records = query.order_by(desc(AnalysisRecord.analysis_time)).offset((page - 1) * size).limit(size).all()

    return HistoryListResponse(
        total=total,
        page=page,
        size=size,
        records=[HistoryRecordSchema.model_validate(r.to_dict()) for r in records],
    )


@router.get("/score-trend/{code}")
async def get_score_trend(
    code: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """获取某代码的评分趋势"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(AnalysisRecord)
        .filter(
            and_(
                AnalysisRecord.code == code,
                AnalysisRecord.score.isnot(None),
                AnalysisRecord.analysis_time >= since,
            )
        )
        .order_by(AnalysisRecord.analysis_time)
        .all()
    )

    return [
        ScoreTrendPoint(
            date=r.analysis_time.strftime("%Y-%m-%d"),
            score=r.score,
        )
        for r in records
    ]


@router.delete("/history/{record_id}")
async def delete_history(record_id: int, db: Session = Depends(get_db)):
    """删除单条历史记录"""
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"message": "删除成功"}


@router.delete("/history")
async def clear_history(db: Session = Depends(get_db)):
    """清空所有历史记录"""
    count = db.query(AnalysisRecord).count()
    db.query(AnalysisRecord).delete()
    db.commit()
    return {"message": f"已清空 {count} 条记录"}
