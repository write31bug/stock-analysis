"""Pydantic 请求/响应模型"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ---- OHLCV 时序数据 ----


class OHLCVItem(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class SeriesPoint(BaseModel):
    date: str
    value: Optional[float] = None


# ---- 分析响应 ----


class AnalyzeResponse(BaseModel):
    stock_info: Dict[str, Any]
    technical_indicators: Dict[str, Any]
    key_levels: Dict[str, Any]
    analysis: Dict[str, Any]
    ohlcv: List[OHLCVItem] = []
    indicator_series: Dict[str, List[SeriesPoint]] = {}


class BatchSubmitRequest(BaseModel):
    codes: List[str]
    market: str = "auto"
    asset_type: str = "stock"
    days: int = 60
    test: bool = False


class BatchSubmitResponse(BaseModel):
    task_id: str
    status: str
    total: int


class BatchStatusResponse(BaseModel):
    task_id: str
    status: str  # running | completed
    progress: int
    total: int
    results: Optional[List[Dict[str, Any]]] = None


# ---- 自选股 ----


class WatchlistItem(BaseModel):
    code: str
    name: str = ""
    group: str = "默认"


class WatchlistResponse(BaseModel):
    message: str
    watchlist: List[WatchlistItem]


class ImportResultItem(BaseModel):
    code: str
    name: str = ""
    status: str  # "added" | "existed" | "skipped"


class ImportResponse(BaseModel):
    message: str
    total: int
    added: int
    existed: int
    skipped: int
    results: List[ImportResultItem]


# ---- 历史记录 ----


class SaveHistoryRequest(BaseModel):
    """保存分析记录请求"""

    stock_info: Dict[str, Any] = {}
    analysis: Dict[str, Any] = {}
    technical_indicators: Dict[str, Any] = {}


class HistoryRecord(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    market: Optional[str] = None
    asset_type: Optional[str] = None
    score: Optional[int] = None
    trend: Optional[str] = None
    recommendation: Optional[str] = None
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    summary: Optional[str] = None
    analysis_time: str


class HistoryListResponse(BaseModel):
    total: int
    page: int
    size: int
    records: List[HistoryRecord]


class ScoreTrendPoint(BaseModel):
    date: str
    score: int


# ---- 价格预警 ----


class PriceAlertCreate(BaseModel):
    code: str
    name: str = ""
    condition_type: str
    target_value: float


class PriceAlertResponse(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    condition_type: str
    target_value: float
    current_price: Optional[float] = None
    triggered: bool
    created_at: str
    triggered_at: Optional[str] = None
