"""数据导出接口"""

import asyncio
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from stock_analysis.analyzer import StockAnalyzer
from stock_analysis.fetcher import StockDataFetcher

from ..database import get_db
from ..models import AnalysisRecord

router = APIRouter(tags=["export"])

analyzer = StockAnalyzer()
fetcher = StockDataFetcher()

# CSV 列定义（分析结果和历史记录共用）
CSV_COLUMNS = [
    "代码",
    "名称",
    "现价",
    "涨跌幅",
    "评分",
    "趋势",
    "建议",
    "MA信号",
    "MACD信号",
    "RSI状态",
    "KDJ信号",
    "分析时间",
]

# 别名，保持向后兼容
ANALYSIS_CSV_COLUMNS = CSV_COLUMNS
HISTORY_CSV_COLUMNS = CSV_COLUMNS


def _extract_signal(indicators: dict, key: str) -> str:
    """从技术指标中提取信号文本"""
    if not indicators:
        return ""
    val = indicators.get(key)
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return str(val)


def _build_analysis_row(result: dict, now_str: str) -> list[str]:
    """从分析结果构建 CSV 行"""
    stock_info = result.get("stock_info", {})
    analysis = result.get("analysis", {})
    ti = result.get("technical_indicators", {})

    return [
        stock_info.get("code", ""),
        stock_info.get("name", ""),
        str(stock_info.get("current_price", "")),
        str(stock_info.get("change_pct", "")),
        str(analysis.get("score", "")),
        analysis.get("trend", ""),
        analysis.get("recommendation", ""),
        _extract_signal(ti, "ma_signal"),
        _extract_signal(ti, "macd_signal"),
        _extract_signal(ti, "rsi_status"),
        _extract_signal(ti, "kdj_signal"),
        now_str,
    ]


def _build_history_row(record: AnalysisRecord) -> list[str]:
    """从历史记录构建 CSV 行"""
    import json

    ti = {}
    if record.indicators_json:
        import contextlib

        with contextlib.suppress(json.JSONDecodeError, TypeError):
            ti = json.loads(record.indicators_json)

    return [
        record.code or "",
        record.name or "",
        str(record.current_price or ""),
        str(record.change_pct or ""),
        str(record.score or ""),
        record.trend or "",
        record.recommendation or "",
        _extract_signal(ti, "ma_signal"),
        _extract_signal(ti, "macd_signal"),
        _extract_signal(ti, "rsi_status"),
        _extract_signal(ti, "kdj_signal"),
        record.analysis_time.strftime("%Y-%m-%d %H:%M:%S") if record.analysis_time else "",
    ]


@router.get("/export/csv")
async def export_analysis_csv(
    codes: str = Query(..., description="逗号分隔的股票代码"),
    market: str = Query("auto"),
    asset_type: str = Query("stock"),
    days: int = Query(60, ge=10, le=500),
    limit: int = Query(10000, ge=1, le=100000),
):
    """导出分析结果为 CSV"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()][:limit]
    if not code_list:
        return StreamingResponse(
            iter(["空代码列表"]),
            media_type="text/plain",
        )

    rows: list[list[str]] = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for code in code_list:
        try:
            result = await asyncio.to_thread(analyzer.analyze, code, market, asset_type, days)
            if "error" not in result:
                rows.append(_build_analysis_row(result, now_str))
            else:
                rows.append([code, "", "", "", "", "", f"错误: {result['error']}", "", "", "", "", now_str])
        except Exception as e:
            rows.append([code, "", "", "", "", "", f"异常: {e}", "", "", "", "", now_str])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(ANALYSIS_CSV_COLUMNS)
    writer.writerows(rows)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename=analysis_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"
        },
    )


@router.get("/export/history")
async def export_history_csv(
    code: str = Query(None),
    trend: str = Query(None),
    start: str = Query(None),
    end: str = Query(None),
    limit: int = Query(10000, ge=1, le=100000),
    db: Session = Depends(get_db),
):
    """导出历史记录为 CSV"""
    query = db.query(AnalysisRecord)

    if code:
        query = query.filter(AnalysisRecord.code == code)
    if trend:
        query = query.filter(AnalysisRecord.trend == trend)
    if start:
        query = query.filter(AnalysisRecord.analysis_time >= start)
    if end:
        try:
            from datetime import timedelta as _td
            end_dt = datetime.strptime(end, "%Y-%m-%d") + _td(hours=23, minutes=59, seconds=59)
        except (ValueError, TypeError):
            end_dt = end + " 23:59:59"
        query = query.filter(AnalysisRecord.analysis_time <= end_dt)

    records = query.order_by(desc(AnalysisRecord.analysis_time)).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(HISTORY_CSV_COLUMNS)
    for record in records:
        writer.writerow(_build_history_row(record))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename=history_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"
        },
    )
