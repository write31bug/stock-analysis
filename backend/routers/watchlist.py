"""自选股接口"""

import re
from typing import List

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from stock_analysis.config import load_config, save_config

from ..schemas import (
    ImportResponse,
    ImportResultItem,
    WatchlistItem,
    WatchlistResponse,
)

router = APIRouter(tags=["watchlist"])

# ── 默认分组 ──
DEFAULT_GROUPS = ["股票", "场内基金", "场外基金", "REITs", "其他"]


def _ensure_default_groups(config: dict):
    """确保默认分组存在"""
    groups = config.get("watchlist_groups", [])
    for g in DEFAULT_GROUPS:
        if g not in groups:
            groups.append(g)
    config["watchlist_groups"] = groups


def _auto_detect_group(code: str) -> str:
    """根据代码前缀自动判断分组"""
    if re.match(r"^(15|51|52|58|56)\d{3}$", code):
        return "场内基金"  # ETF
    if re.match(r"^16\d{4}$", code):
        return "场内基金"  # LOF
    if re.match(r"^50\d{4}$", code):
        return "REITs"  # 公募REITs
    if re.match(r"^(00|01|02|03|05|09)\d{4}$", code):
        # 6位数以 00/01/02/03/05/09 开头：场外基金（排除 000001-000999 已知股票段）
        num = int(code)
        if num < 1000:
            return "股票"  # 000001-000999 段多为股票（如 000001 平安银行）
        return "场外基金"
    if re.match(r"^(6|9)\d{5}$", code):
        return "股票"  # 沪市主板/科创板
    if re.match(r"^[234]\d{5}$", code):
        return "股票"  # 深市主板/中小板/创业板
    if re.match(r"^(4|8)\d{5}$", code):
        return "股票"  # 新三板/北交所
    if re.match(r"^HK\.", code):
        return "股票"  # 港股
    # 纯字母 = 美股
    if re.match(r"^[A-Za-z]+$", code):
        return "股票"
    return "其他"


def _normalize_watchlist(raw: list) -> List[WatchlistItem]:
    """将配置中的自选股列表统一为 WatchlistItem 格式"""
    items = []
    for w in raw:
        if isinstance(w, str):
            items.append(WatchlistItem(code=w, name="", group="默认"))
        elif isinstance(w, dict):
            items.append(
                WatchlistItem(
                    code=w.get("code", ""),
                    name=w.get("name", ""),
                    group=w.get("group", "默认"),
                )
            )
    return items


@router.get("/watchlist", response_model=List[WatchlistItem])
async def get_watchlist(group: str = Query(None)):
    """获取自选股列表，可按分组筛选"""
    config = load_config()
    items = _normalize_watchlist(config.get("watchlist", []))
    if group is not None:
        items = [item for item in items if item.group == group]
    return items


@router.get("/watchlist/groups", response_model=List[str])
async def get_watchlist_groups():
    """获取所有分组名称"""
    config = load_config()
    items = _normalize_watchlist(config.get("watchlist", []))
    groups = sorted(set(item.group for item in items))
    return groups


@router.post("/watchlist", response_model=WatchlistResponse)
async def add_to_watchlist(item: WatchlistItem):
    """添加到自选股（自动判断分组）"""
    config = load_config()
    _ensure_default_groups(config)
    watchlist = config.get("watchlist", [])

    # 检查是否已存在
    for w in watchlist:
        code = w if isinstance(w, str) else w.get("code", "")
        if code == item.code:
            return WatchlistResponse(
                message="已存在",
                watchlist=_normalize_watchlist(watchlist),
            )

    # 如果分组为"默认"或空，自动判断
    group = item.group
    if not group or group == "默认":
        group = _auto_detect_group(item.code)

    watchlist.append({"code": item.code, "name": item.name, "group": group})
    config["watchlist"] = watchlist
    save_config(config)
    return WatchlistResponse(
        message="添加成功",
        watchlist=_normalize_watchlist(watchlist),
    )


class GroupNameRequest(BaseModel):
    name: str


@router.post("/watchlist/group")
async def create_or_rename_group(req: GroupNameRequest):
    """创建或重命名分组（确保分组名称存在）"""
    config = load_config()
    groups = config.get("watchlist_groups", [])
    if req.name not in groups:
        groups.append(req.name)
        config["watchlist_groups"] = groups
        save_config(config)
        return {"message": f"分组 '{req.name}' 创建成功"}
    return {"message": f"分组 '{req.name}' 已存在"}


@router.delete("/watchlist/group/{name}")
async def delete_group(name: str):
    """删除分组，将该分组下的自选股移到默认分组"""
    if name == "默认":
        raise HTTPException(status_code=400, detail="不能删除默认分组")

    config = load_config()
    watchlist = config.get("watchlist", [])

    changed = False
    for _i, w in enumerate(watchlist):
        if isinstance(w, dict) and w.get("group") == name:
            w["group"] = "默认"
            changed = True

    if not changed:
        raise HTTPException(status_code=404, detail=f"分组 '{name}' 不存在或没有成员")

    # 从分组列表中移除
    groups = config.get("watchlist_groups", [])
    if name in groups:
        groups.remove(name)
        config["watchlist_groups"] = groups

    config["watchlist"] = watchlist
    save_config(config)
    return {"message": f"分组 '{name}' 已删除，成员已移至默认分组"}


@router.delete("/watchlist/{code}", response_model=WatchlistResponse)
async def remove_from_watchlist(code: str):
    """从自选股删除"""
    config = load_config()
    watchlist = config.get("watchlist", [])

    original_len = len(watchlist)
    watchlist = [w for w in watchlist if (w if isinstance(w, str) else w.get("code", "")) != code]

    if len(watchlist) == original_len:
        raise HTTPException(status_code=404, detail=f"{code} 不在自选股中")

    config["watchlist"] = watchlist
    save_config(config)
    return WatchlistResponse(
        message="删除成功",
        watchlist=_normalize_watchlist(watchlist),
    )


@router.post("/watchlist/import", response_model=ImportResponse)
async def import_watchlist(
    file: UploadFile = File(...),
    group: str = Query("默认"),
    code_col: str = Query("代码"),
    name_col: str = Query("名称"),
):
    """从 Excel/CSV 文件导入自选股

    支持的文件格式：.xlsx, .xls, .csv
    自动跳过汇总行和无效代码行
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in ("xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls / .csv 文件")

    try:
        content = await file.read()
        if suffix == "csv":
            df = pd.read_csv(BytesIO(content), dtype=str)
        else:
            df = pd.read_excel(BytesIO(content), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}") from None

    if code_col not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"未找到 '{code_col}' 列，当前列名: {df.columns.tolist()}",
        )

    config = load_config()
    _ensure_default_groups(config)
    watchlist = config.get("watchlist", [])

    existing_codes = set()
    for w in watchlist:
        c = w if isinstance(w, str) else w.get("code", "")
        existing_codes.add(str(c).strip())

    added = 0
    existed = 0
    skipped = 0
    results: List[ImportResultItem] = []

    for _, row in df.iterrows():
        code = str(row.get(code_col, "")).strip()
        name = str(row.get(name_col, "")).strip() if name_col in df.columns else ""

        # 跳过无效行：空代码、汇总行、表头重复
        if not code or code in ("代码", "汇总", "合计", "code", "Code"):
            skipped += 1
            results.append(ImportResultItem(code=code, name=name, status="skipped"))
            continue

        # 自动判断分组（覆盖传入的默认分组）
        auto_group = _auto_detect_group(code)

        if code in existing_codes:
            existed += 1
            results.append(ImportResultItem(code=code, name=name, status="existed"))
            continue

        watchlist.append({"code": code, "name": name, "group": auto_group})
        existing_codes.add(code)
        added += 1
        results.append(ImportResultItem(code=code, name=name, status="added"))

    config["watchlist"] = watchlist
    save_config(config)

    return ImportResponse(
        message=f"导入完成：新增 {added}，已存在 {existed}，跳过 {skipped}",
        total=len(results),
        added=added,
        existed=existed,
        skipped=skipped,
        results=results,
    )
