"""分析接口"""

import asyncio
import threading
import uuid
from collections import OrderedDict
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from stock_analysis.analyzer import StockAnalyzer
from stock_analysis.fetcher import StockDataFetcher

from ..schemas import (
    AnalyzeResponse,
    BatchStatusResponse,
    BatchSubmitRequest,
    BatchSubmitResponse,
    OHLCVItem,
    SeriesPoint,
)
from ..services.cache_service import cache_service

router = APIRouter(tags=["analyze"])

analyzer = StockAnalyzer()
fetcher = StockDataFetcher()

# 批量任务存储：限制最大数量，避免内存泄漏
_batch_tasks: OrderedDict = {}
_batch_lock = threading.Lock()
_MAX_BATCH_TASKS = 100


def _cleanup_old_batch_tasks():
    """清理旧任务，保留最新的 _MAX_BATCH_TASKS 条"""
    while len(_batch_tasks) > _MAX_BATCH_TASKS:
        _batch_tasks.popitem(last=False)


def _extract_ohlcv(df: pd.DataFrame) -> List[OHLCVItem]:
    """从 DataFrame 提取 OHLCV 时序数据"""
    cols = ["date", "open", "high", "low", "close", "volume"]
    available_cols = [c for c in cols if c in df.columns]
    records = df[available_cols].to_dict("records")
    return [
        OHLCVItem(
            date=str(r["date"])[:10],
            open=round(float(r.get("open", 0)), 4),
            high=round(float(r.get("high", 0)), 4),
            low=round(float(r.get("low", 0)), 4),
            close=round(float(r["close"]), 4),
            volume=float(r.get("volume", 0)),
        )
        for r in records
    ]


def _compute_indicator_series(df: pd.DataFrame) -> Dict[str, List[SeriesPoint]]:
    """重新计算技术指标并提取完整时序数据（用于图表渲染）"""
    series = {}
    dates = [str(d)[:10] for d in df["date"]]
    n = len(dates)

    # MA
    for period in [5, 10, 20, 60]:
        if n >= period:
            ma = df["close"].rolling(window=period).mean()
            series[f"MA{period}"] = [
                SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, ma)
            ]

    # MACD
    if n >= 26:
        ema_fast = df["close"].ewm(span=12, adjust=False).mean()
        ema_slow = df["close"].ewm(span=26, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_hist = (dif - dea) * 2

        series["DIF"] = [
            SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, dif)
        ]
        series["DEA"] = [
            SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, dea)
        ]
        series["MACD"] = [
            SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, macd_hist)
        ]

    # RSI
    delta = df["close"].diff()
    for period in [6, 12, 24]:
        if n >= period:
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            series[f"RSI{period}"] = [
                SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, rsi)
            ]

    # KDJ
    if n >= 9:
        low_list = df["low"].rolling(window=9, min_periods=1).min()
        high_list = df["high"].rolling(window=9, min_periods=1).max()
        rsv = (df["close"] - low_list) / (high_list - low_list) * 100
        rsv = rsv.fillna(50)
        k = rsv.ewm(com=2, adjust=False).mean()
        kdj_d = k.ewm(com=2, adjust=False).mean()
        kdj_j = 3 * k - 2 * kdj_d

        series["K"] = [SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, k)]
        series["D"] = [SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, kdj_d)]
        series["J"] = [SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, kdj_j)]

    # BOLL
    if n >= 20:
        middle = df["close"].rolling(window=20).mean()
        std = df["close"].rolling(window=20).std()
        upper = middle + 2.0 * std
        lower = middle - 2.0 * std

        series["BOLL_UPPER"] = [
            SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, upper)
        ]
        series["BOLL_MIDDLE"] = [
            SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, middle)
        ]
        series["BOLL_LOWER"] = [
            SeriesPoint(date=d, value=round(float(v), 4) if pd.notna(v) else None) for d, v in zip(dates, lower)
        ]

    # OBV (On Balance Volume)
    if "volume" in df.columns and n >= 2:
        close_change = df["close"].diff()
        obv = (df["volume"] * close_change.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()
        series["OBV"] = [
            SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, obv)
        ]

    # CCI (Commodity Channel Index)
    if n >= 20:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        tp_sma = typical_price.rolling(window=20).mean()
        mean_dev = typical_price.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        cci = (typical_price - tp_sma) / (0.015 * mean_dev)
        series["CCI"] = [
            SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, cci)
        ]

    # WR (Williams %R)
    if n >= 14:
        highest_high = df["high"].rolling(window=14, min_periods=1).max()
        lowest_low = df["low"].rolling(window=14, min_periods=1).min()
        wr = (highest_high - df["close"]) / (highest_high - lowest_low) * -100
        series["WR"] = [
            SeriesPoint(date=d, value=round(float(v), 2) if pd.notna(v) else None) for d, v in zip(dates, wr)
        ]

    return series


@router.get("/analyze/{code}", response_model=AnalyzeResponse)
async def analyze_stock(
    code: str,
    market: str = Query("auto"),
    asset_type: str = Query("stock"),
    days: int = Query(60, ge=10, le=500),
    test: bool = Query(False),
):
    """单股技术分析"""
    # 生成缓存键
    cache_key = f"analyze:{code}:{market}:{asset_type}:{days}:{test}"
    
    # 尝试从缓存获取
    cached_result = cache_service.get(cache_key)
    if cached_result:
        return cached_result

    if test:
        result = await asyncio.to_thread(analyzer.analyze_with_mock_data, code, market, asset_type, days, return_df=True)
    else:
        result = await asyncio.to_thread(analyzer.analyze, code, market, asset_type, days, return_df=True)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # 获取 DataFrame 用于提取时序数据
    ohlcv = []
    indicator_series = {}
    df = result.pop("_df", None)
    if df is not None and not df.empty:
        ohlcv = _extract_ohlcv(df)
        indicator_series = _compute_indicator_series(df)

    result["ohlcv"] = [item.model_dump() for item in ohlcv]
    result["indicator_series"] = {k: [p.model_dump() for p in v] for k, v in indicator_series.items()}

    # 存入缓存
    cache_service.set(cache_key, result)

    return result


@router.post("/batch", response_model=BatchSubmitResponse)
async def submit_batch(req: BatchSubmitRequest):
    """提交批量分析任务"""
    # 验证代码数组
    if not req.codes:
        raise HTTPException(status_code=400, detail="代码数组不能为空")
    
    # 验证代码数量限制
    if len(req.codes) > 100:
        raise HTTPException(status_code=400, detail="代码数量不能超过100个")
    
    # 验证每个代码的格式
    import re
    for code in req.codes:
        if not code or not code.strip():
            raise HTTPException(status_code=400, detail="代码不能为空")
        if len(code) > 20:
            raise HTTPException(status_code=400, detail=f"代码 {code} 长度不能超过20个字符")
        # 验证代码格式（只允许字母、数字和点）
        if not re.match(r"^[A-Za-z0-9.]+$", code):
            raise HTTPException(status_code=400, detail=f"代码 {code} 只能包含字母、数字和点")
    
    task_id = str(uuid.uuid4())[:8]
    with _batch_lock:
        _cleanup_old_batch_tasks()
        _batch_tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "progress": 0,
            "total": len(req.codes),
            "results": [],
        }

    # 后台线程执行批量分析，5并发 + 全部完成后一次性写入
    def _run_batch():
        try:
            import logging
            from concurrent.futures import ThreadPoolExecutor, as_completed

            _logger = logging.getLogger(__name__)
            results = []
            completed = 0
            failed = 0
            success_results = []

            def _do_one(code: str) -> dict:
                try:
                    if req.test:
                        result = analyzer.analyze_with_mock_data(code, req.market, req.asset_type)
                    else:
                        result = analyzer.analyze(code, req.market, req.asset_type, req.days)
                    return result
                except Exception as e:
                    return {"error": str(e), "stock_info": {"code": code}}

            with ThreadPoolExecutor(max_workers=5) as pool:
                future_to_code = {pool.submit(_do_one, code): code for code in req.codes}
                for future in as_completed(future_to_code):
                    code = future_to_code[future]
                    try:
                        result = future.result(timeout=30)
                        if "error" in result:
                            failed += 1
                        else:
                            success_results.append(result)
                        results.append(result)
                    except Exception as e:
                        failed += 1
                        results.append({"error": str(e), "stock_info": {"code": code}})

                    completed += 1
                    with _batch_lock:
                        _batch_tasks[task_id]["progress"] = completed
                        _batch_tasks[task_id]["completed"] = completed
                        _batch_tasks[task_id]["failed"] = failed
                        _batch_tasks[task_id]["results"] = results

            # 全部完成后一次性批量写入数据库
            if success_results:
                try:
                    from ..database import SessionLocal
                    from ..services.analysis_service import save_analysis_result

                    db = SessionLocal()
                    try:
                        for r in success_results:
                            save_analysis_result(db, r)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        _logger.error("批量写入数据库失败: %s", e)
                    finally:
                        db.close()
                except Exception as e:
                    _logger.error("批量写入数据库异常: %s", e)

            with _batch_lock:
                _batch_tasks[task_id]["status"] = "completed"
        except Exception as e:
            with _batch_lock:
                _batch_tasks[task_id]["status"] = "completed"
                _batch_tasks[task_id]["error"] = str(e)

    threading.Thread(target=_run_batch, daemon=True).start()

    return BatchSubmitResponse(task_id=task_id, status="running", total=len(req.codes))


@router.get("/batch/{task_id}", response_model=BatchStatusResponse)
async def get_batch_status(task_id: str):
    """查询批量分析进度"""
    with _batch_lock:
        task = _batch_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return BatchStatusResponse(**task)
