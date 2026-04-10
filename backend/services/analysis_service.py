"""分析服务 - 公共模块"""

import json
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session

from ..models import AnalysisRecord, Portfolio


def save_analysis_result(db: Session, result: Dict[str, Any], portfolios: Dict[str, Any] | None = None) -> None:
    """将分析结果存入数据库，并更新 Portfolio 的分析时间"""
    if "error" in result:
        return

    stock_info = result.get("stock_info", {})
    analysis = result.get("analysis", {})
    indicators = result.get("technical_indicators", {})
    code = stock_info.get("code", "")

    if not code:
        return

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
    if portfolios is not None:
        portfolio = portfolios.get(code)
    else:
        portfolio = db.query(Portfolio).filter(Portfolio.code == code).first()
    if portfolio:
        portfolio.updated_at = datetime.now(timezone.utc)
