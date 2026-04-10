"""价格预警接口"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from stock_analysis.fetcher import StockDataFetcher

from ..database import get_db
from ..models import PriceAlert
from ..schemas import PriceAlertCreate, PriceAlertResponse

router = APIRouter(tags=["alerts"])

fetcher = StockDataFetcher()


def _alert_to_schema(a: PriceAlert) -> PriceAlertResponse:
    """将 ORM 对象转换为响应 schema"""
    return PriceAlertResponse(
        id=a.id,
        code=a.code,
        name=a.name,
        condition_type=a.condition_type,
        target_value=a.target_value,
        current_price=a.current_price,
        triggered=a.triggered,
        created_at=a.created_at.isoformat() if a.created_at else "",
        triggered_at=a.triggered_at.isoformat() if a.triggered_at else None,
    )


@router.get("/alerts", response_model=list[PriceAlertResponse])
async def list_alerts(db: Session = Depends(get_db)):
    """获取所有价格预警"""
    alerts = db.query(PriceAlert).order_by(PriceAlert.created_at.desc()).all()
    return [_alert_to_schema(a) for a in alerts]


@router.post("/alerts", response_model=PriceAlertResponse)
async def create_alert(req: PriceAlertCreate, db: Session = Depends(get_db)):
    """创建价格预警"""
    alert = PriceAlert(
        code=req.code,
        name=req.name,
        condition_type=req.condition_type,
        target_value=req.target_value,
    )
    db.add(alert)
    try:
        db.commit()
        db.refresh(alert)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="预警已存在（相同代码、条件类型和目标值）") from None
    return _alert_to_schema(alert)


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """删除价格预警"""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    db.delete(alert)
    db.commit()
    return {"message": "删除成功"}


@router.post("/alerts/check")
async def check_alerts(db: Session = Depends(get_db)):
    """检查所有未触发的预警"""
    untriggered = db.query(PriceAlert).filter(PriceAlert.triggered.is_(False)).all()
    if not untriggered:
        return {"message": "没有待检查的预警", "triggered_count": 0}

    triggered_count = 0
    # 收集需要查询的代码
    codes = list({a.code for a in untriggered})
    price_map: dict[str, tuple[float, str]] = {}

    for code in codes:
        try:
            normalized_code, _, _ = await asyncio.to_thread(fetcher.normalize_stock_code, code, "auto", "stock")
            df = await asyncio.to_thread(fetcher.fetch_data, normalized_code, "auto", "stock", 5)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                price_map[code] = (float(latest["close"]), str(latest.get("name", "")))
        except Exception:
            continue

    now = datetime.now(timezone.utc)
    for alert in untriggered:
        if alert.code not in price_map:
            continue

        current_price, name = price_map[alert.code]
        alert.current_price = current_price
        if name:
            alert.name = name

        triggered = False
        if (
            alert.condition_type == "above"
            and current_price > alert.target_value
            or alert.condition_type == "below"
            and current_price < alert.target_value
        ):
            triggered = True
        elif alert.condition_type == "pct_change_above":
            # 需要前一日收盘价来计算涨跌幅
            if alert.code in price_map:
                try:
                    normalized_code, _, _ = await asyncio.to_thread(
                        fetcher.normalize_stock_code, alert.code, "auto", "stock"
                    )
                    df = await asyncio.to_thread(fetcher.fetch_data, normalized_code, "auto", "stock", 10)
                    if df is not None and len(df) >= 2:
                        prev_close = float(df.iloc[-2]["close"])
                        pct_change = (current_price - prev_close) / prev_close * 100
                        if pct_change > alert.target_value:
                            triggered = True
                except Exception:
                    pass
        elif alert.condition_type == "pct_change_below":
            try:
                normalized_code, _, _ = await asyncio.to_thread(
                    fetcher.normalize_stock_code, alert.code, "auto", "stock"
                )
                df = await asyncio.to_thread(fetcher.fetch_data, normalized_code, "auto", "stock", 10)
                if df is not None and len(df) >= 2:
                    prev_close = float(df.iloc[-2]["close"])
                    pct_change = (current_price - prev_close) / prev_close * 100
                    if pct_change < alert.target_value:
                        triggered = True
            except Exception:
                pass

        if triggered:
            alert.triggered = True
            alert.triggered_at = now
            triggered_count += 1

    db.commit()
    return {"message": f"检查完成，触发 {triggered_count} 条预警", "triggered_count": triggered_count}
