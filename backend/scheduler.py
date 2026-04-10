"""定时采集服务：定期分析自选股并存入数据库"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import AnalysisRecord

logger = logging.getLogger(__name__)

# 全局状态
_scheduler_state: Dict[str, Any] = {
    "running": False,
    "last_run": None,
    "last_status": None,
    "next_run": None,
    "interval": 180,  # 3 分钟
    "total_collected": 0,
    "total_failed": 0,
}
_state_lock = threading.Lock()


def get_scheduler_state() -> Dict[str, Any]:
    with _state_lock:
        return dict(_scheduler_state)


def _get_watchlist_codes() -> list:
    """从配置文件读取自选股代码列表"""
    try:
        from stock_analysis.config import load_config

        config = load_config()
        watchlist = config.get("watchlist", [])
        codes = []
        for w in watchlist:
            if isinstance(w, str):
                codes.append(w)
            elif isinstance(w, dict):
                codes.append(w.get("code", ""))
        return [c for c in codes if c.strip()]
    except Exception as e:
        logger.error(f"读取自选股列表失败: {e}")
        return []


def _analyze_one(code: str) -> Dict[str, Any]:
    """分析单只股票"""
    from stock_analysis.analyzer import StockAnalyzer
    from stock_analysis.fetcher import StockDataFetcher

    fetcher = StockDataFetcher()
    analyzer = StockAnalyzer()

    # 自动识别类型
    normalized_code, market, asset_type = fetcher.normalize_stock_code(code, "auto", "stock")

    try:
        result = analyzer.analyze(normalized_code, market, asset_type, days=60)
        return result
    except Exception as e:
        logger.warning(f"分析 {code} 失败: {e}")
        return {"error": str(e), "stock_info": {"code": code}}


def _save_to_db(db: Session, result: Dict[str, Any], portfolios: Dict[str, Any] | None = None) -> None:
    """将分析结果存入数据库，并更新 Portfolio 的分析时间"""
    if "error" in result:
        return

    stock_info = result.get("stock_info", {})
    analysis = result.get("analysis", {})
    indicators = result.get("technical_indicators", {})
    code = stock_info.get("code", "")

    if not code:
        return

    import json

    # 删除旧记录，改用 merge 实现 upsert
    record = AnalysisRecord(
        code=code,
        name=stock_info.get("name", ""),
        market=stock_info.get("market", ""),
        asset_type=stock_info.get("asset_type", "stock"),
        score=analysis.get("score"),
        trend=analysis.get("trend", ""),
        recommendation=analysis.get("recommendation", ""),
        current_price=stock_info.get("current_price"),
        change_pct=stock_info.get("change_pct"),
        summary=analysis.get("summary", ""),
        indicators_json=json.dumps(indicators, ensure_ascii=False, default=str) if indicators else None,
        analysis_time=datetime.now(timezone.utc),
    )
    db.merge(record)

    # 更新 Portfolio 表的 updated_at（分析成功时）
    from .models import Portfolio
    if portfolios is not None:
        portfolio = portfolios.get(code)
    else:
        portfolio = db.query(Portfolio).filter(Portfolio.code == code).first()
    if portfolio:
        portfolio.updated_at = datetime.now(timezone.utc)


def run_collect_once() -> Dict[str, Any]:
    """执行一次采集（手动或定时调用），5并发"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    codes = _get_watchlist_codes()
    if not codes:
        return {"collected": 0, "failed": 0, "message": "自选股列表为空"}

    collected = 0
    failed = 0
    errors = []

    def _do_one(code: str) -> Dict[str, Any]:
        try:
            return _analyze_one(code)
        except Exception as e:
            return {"error": str(e), "stock_info": {"code": code}}

    # 并发采集所有数据（不涉及数据库）
    all_results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        future_to_code = {pool.submit(_do_one, code): code for code in codes}
        for future in as_completed(future_to_code, timeout=300):
            code = future_to_code[future]
            try:
                result = future.result(timeout=30)
                if "error" in result:
                    failed += 1
                    errors.append({"code": code, "error": result.get("error", "")})
                else:
                    all_results.append(result)
                    collected += 1
            except Exception as e:
                failed += 1
                errors.append({"code": code, "error": str(e)})

    # 采集完成后，一次性批量写入数据库（减少锁竞争）
    if all_results:
        db = SessionLocal()
        try:
            from .models import Portfolio
            portfolios = {p.code: p for p in db.query(Portfolio).all()}
            for result in all_results:
                _save_to_db(db, result, portfolios=portfolios)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"批量写入数据库失败: {e}")
        finally:
            db.close()

    return {"collected": collected, "failed": failed, "errors": errors, "message": f"采集完成：成功 {collected}，失败 {failed}"}


def _scheduler_loop():
    """定时采集主循环"""
    global _scheduler_state
    logger.info("定时采集服务已启动，间隔 %d 秒", _scheduler_state["interval"])

    while _scheduler_state["running"]:
        try:
            start = time.time()
            logger.info(f"开始采集，共 {len(_get_watchlist_codes())} 只自选股")

            result = run_collect_once()

            elapsed = time.time() - start
            with _state_lock:
                _scheduler_state["last_run"] = datetime.now(timezone.utc).isoformat()
                _scheduler_state["last_status"] = result
                _scheduler_state["total_collected"] += result["collected"]
                _scheduler_state["total_failed"] += result["failed"]
                _scheduler_state["next_run"] = datetime.now(timezone.utc).timestamp() + _scheduler_state["interval"]

            logger.info(
                f"采集完成: 成功 {result['collected']}, 失败 {result['failed']}, 耗时 {elapsed:.1f}s"
            )
        except Exception as e:
            logger.error(f"采集任务异常: {e}", exc_info=True)

        # 等待到下一次
        for _ in range(int(_scheduler_state["interval"])):
            if not _scheduler_state["running"]:
                break
            time.sleep(1)


_scheduler_thread: threading.Thread | None = None


def start_scheduler(interval: int = 180):
    """启动定时采集服务"""
    global _scheduler_state, _scheduler_thread
    with _state_lock:
        if _scheduler_state["running"]:
            return
        _scheduler_state["running"] = True
        _scheduler_state["interval"] = interval
        _scheduler_state["next_run"] = datetime.now(timezone.utc).timestamp() + interval

    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="scheduler")
    _scheduler_thread.start()


def stop_scheduler() -> threading.Thread | None:
    """停止定时采集服务，返回旧线程引用"""
    global _scheduler_state
    with _state_lock:
        _scheduler_state["running"] = False
    logger.info("定时采集服务已停止")
    return _scheduler_thread
