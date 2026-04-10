"""持仓数据接口"""

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Portfolio

router = APIRouter(tags=["portfolio"])

# Excel 列名 → 数据库字段名 映射（兼容不同券商导出格式）
COL_MAP = {
    "代码": "code",
    "名称": "name",
    "持有金额": "hold_amount",
    "持仓金额": "hold_amount",
    "市值": "hold_amount",
    "当日盈亏": "day_pnl",
    "今日盈亏": "day_pnl",
    "当日盈亏率": "day_pnl_pct",
    "今日盈亏率": "day_pnl_pct",
    "当日涨跌": "day_pnl",
    "持有盈亏": "hold_pnl",
    "持仓盈亏": "hold_pnl",
    "累计盈亏": "total_pnl",
    "持有盈亏率": "hold_pnl_pct",
    "持仓盈亏率": "hold_pnl_pct",
    "累计盈亏率": "total_pnl_pct",
    "本周盈亏": "week_pnl",
    "本月盈亏": "month_pnl",
    "今年盈亏": "year_pnl",
    "仓位占比": "position_pct",
    "持仓占比": "position_pct",
    "仓位": "position_pct",
    "持有数量": "hold_quantity",
    "持仓数量": "hold_quantity",
    "持仓股数": "hold_quantity",
    "数量": "hold_quantity",
    "持仓天数": "hold_days",
    "最新涨幅": "latest_change_pct",
    "最新价": "latest_price",
    "现价": "latest_price",
    "单位成本": "unit_cost",
    "成本价": "unit_cost",
    "回本涨幅": "breakeven_pct",
    "近1月涨幅": "month_1_pct",
    "近3月涨幅": "month_3_pct",
    "近6月涨幅": "month_6_pct",
    "近1年涨幅": "year_1_pct",
}

SKIP_CODES = {"代码", "汇总", "合计", "code", "Code", ""}


def _safe_float(val) -> float | None:
    if val is None or str(val).strip() in ("", "nan", "NaN", "None", "-"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    f = _safe_float(val)
    return int(f) if f is not None else None


@router.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    """获取全部持仓数据"""
    items = db.query(Portfolio).order_by(Portfolio.hold_amount.desc()).all()
    return [p.to_dict() for p in items]


@router.get("/portfolio/summary")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """获取持仓汇总"""
    total_amount = db.query(func.sum(Portfolio.hold_amount)).scalar() or 0
    total_day_pnl = db.query(func.sum(Portfolio.day_pnl)).scalar() or 0
    total_hold_pnl = db.query(func.sum(Portfolio.hold_pnl)).scalar() or 0
    total_year_pnl = db.query(func.sum(Portfolio.year_pnl)).scalar() or 0
    count = db.query(func.count(Portfolio.id)).scalar() or 0
    return {
        "count": count,
        "total_amount": round(total_amount, 2),
        "total_day_pnl": round(total_day_pnl, 2),
        "total_hold_pnl": round(total_hold_pnl, 2),
        "total_year_pnl": round(total_year_pnl, 2),
        "day_pnl_pct": round(total_day_pnl / total_amount * 100, 4) if total_amount else 0,
        "hold_pnl_pct": round(total_hold_pnl / total_amount * 100, 4) if total_amount else 0,
    }


@router.post("/portfolio/import")
async def import_portfolio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """从 Excel/CSV 导入持仓数据（增量更新：存在的更新，不存在的新增）"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    # 检查文件大小限制（5MB）
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小不能超过 5MB")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in ("xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls / .csv 文件")

    try:
        content = await file.read()
        # 兜底检查：客户端未发送 Content-Length 时用实际内容大小判断
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="文件大小不能超过 5MB")
        if suffix == "csv":
            df = pd.read_csv(BytesIO(content), dtype=str)
        else:
            df = pd.read_excel(BytesIO(content), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}") from None

    if "代码" not in df.columns:
        raise HTTPException(status_code=400, detail=f"未找到'代码'列，当前列: {df.columns.tolist()}")

    added = 0
    updated = 0
    skipped = 0

    # 批量获取已有记录，避免 N+1 查询
    existing_records = db.query(Portfolio).all()
    existing_map = {r.code: r for r in existing_records}

    for _, row in df.iterrows():
        code = str(row.get("代码", "")).strip()
        if code in SKIP_CODES:
            skipped += 1
            continue

        name = str(row.get("名称", "")).strip() if "名称" in df.columns else ""
        if name in ("nan", "None", "NaN"):
            name = ""

        # 查找是否已存在（从预加载的 map 中查找）
        existing = existing_map.get(code)

        if existing:
            # 更新已有记录
            if name:
                existing.name = name
            for col_name, field_name in COL_MAP.items():
                if col_name in ("代码", "名称"):
                    continue
                if col_name in df.columns:
                    val = row.get(col_name)
                    parsed = _safe_int(val) if field_name == "hold_days" else _safe_float(val)
                    if parsed is not None:
                        setattr(existing, field_name, parsed)
            updated += 1
        else:
            # 新增记录
            p = Portfolio(code=code, name=name)
            for col_name, field_name in COL_MAP.items():
                if col_name in ("代码", "名称"):
                    continue
                if col_name in df.columns:
                    val = row.get(col_name)
                    parsed = _safe_int(val) if field_name == "hold_days" else _safe_float(val)
                    if parsed is not None:
                        if getattr(p, field_name) is None:
                            setattr(p, field_name, parsed)
            db.add(p)
            added += 1

    db.commit()
    return {
        "message": f"导入完成：新增 {added}，更新 {updated}，跳过 {skipped}",
        "added": added,
        "updated": updated,
        "skipped": skipped,
    }


@router.delete("/portfolio/{code}")
async def delete_portfolio_item(code: str, db: Session = Depends(get_db)):
    """删除单条持仓"""
    item = db.query(Portfolio).filter(Portfolio.code == code).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{code} 不在持仓中")
    db.delete(item)
    db.commit()
    return {"message": f"已删除 {code} ({item.name})"}


@router.delete("/portfolio")
async def clear_portfolio(db: Session = Depends(get_db)):
    """清空全部持仓"""
    count = db.query(func.count(Portfolio.id)).scalar() or 0
    db.query(Portfolio).delete()
    db.commit()
    return {"message": f"已清空 {count} 条持仓"}
