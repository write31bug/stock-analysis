"""pytest 公共 fixtures"""

import logging
import os
from datetime import datetime

# 测试环境强制使用 SQLite 内存数据库（必须在 backend 模块导入之前）
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import numpy as np
import pandas as pd
import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    """测试环境禁用 scheduler 自动启动，防止 daemon 线程发起真实网络请求"""
    monkeypatch.setattr("backend.scheduler.start_scheduler", lambda *a, **k: None)
    monkeypatch.setattr("backend.scheduler.stop_scheduler", lambda: None)


@pytest.fixture(autouse=True)
def disable_network_requests(monkeypatch):
    """全局禁用所有网络请求，避免测试中发起真实 HTTP"""
    monkeypatch.setattr(
        "stock_analysis.fetcher.StockDataFetcher.fetch_stock_data_sina",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "stock_analysis.fetcher.StockDataFetcher.fetch_stock_data_akshare",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "stock_analysis.fetcher.StockDataFetcher.fetch_stock_data_yfinance",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "stock_analysis.fetcher.StockDataFetcher.fetch_fund_data_akshare",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "stock_analysis.fetcher.StockDataFetcher.fetch_quote",
        lambda *a, **k: None,
    )


@pytest.fixture
def sample_df():
    """生成 60 天模拟行情 DataFrame，有明确趋势和极值点"""
    np.random.seed(42)
    base_price = 100.0
    dates = pd.date_range(end=datetime(2026, 4, 9), periods=60, freq="D")

    # 上涨趋势 + 一些波动
    trend = np.linspace(0, 20, 60)
    noise = np.random.normal(0, 2, 60)
    prices = base_price + trend + noise

    # 确保 high >= close >= low
    high = prices + np.abs(np.random.normal(0, 1, 60))
    low = prices - np.abs(np.random.normal(0, 1, 60))
    open_ = low + np.random.uniform(0, 1, 60) * (high - low)

    df = pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": prices,
            "volume": np.random.uniform(1e6, 1e8, 60).astype(int),
        }
    )
    df["pct_change"] = df["close"].pct_change() * 100
    return df


@pytest.fixture
def short_df():
    """只有 10 天数据的 DataFrame（用于测试数据不足场景）"""
    np.random.seed(99)
    dates = pd.date_range(end=datetime(2026, 4, 9), periods=10, freq="D")
    prices = 50 + np.random.normal(0, 1, 10)
    df = pd.DataFrame(
        {
            "date": dates,
            "open": prices - 0.5,
            "high": prices + 1,
            "low": prices - 1,
            "close": prices,
            "volume": np.random.uniform(1e6, 1e8, 10).astype(int),
        }
    )
    df["pct_change"] = df["close"].pct_change() * 100
    return df


@pytest.fixture
def zero_volume_df():
    """全零成交量的 DataFrame"""
    np.random.seed(77)
    dates = pd.date_range(end=datetime(2026, 4, 9), periods=60, freq="D")
    prices = 100 + np.random.normal(0, 2, 60)
    df = pd.DataFrame(
        {
            "date": dates,
            "open": prices - 0.3,
            "high": prices + 0.5,
            "low": prices - 0.5,
            "close": prices,
            "volume": np.zeros(60),
        }
    )
    df["pct_change"] = df["close"].pct_change() * 100
    return df


@pytest.fixture
def fund_df():
    """基金类型 DataFrame（open=high=low=close）"""
    np.random.seed(55)
    dates = pd.date_range(end=datetime(2026, 4, 9), periods=60, freq="D")
    nav = 1.5 + np.random.normal(0, 0.01, 60).cumsum()
    df = pd.DataFrame(
        {
            "date": dates,
            "open": nav,
            "high": nav,
            "low": nav,
            "close": nav,
            "volume": np.zeros(60),
        }
    )
    df["pct_change"] = df["close"].pct_change() * 100
    return df


@pytest.fixture
def divergence_bull_df():
    """构造底背离数据：价格新低但 DIF 升高"""
    np.random.seed(123)
    dates = pd.date_range(end=datetime(2026, 4, 9), periods=30, freq="D")
    # 价格先跌后涨再跌（两个低点，第二个更低）
    prices = np.concatenate(
        [
            np.linspace(110, 100, 10),
            np.linspace(100, 108, 10),
            np.linspace(108, 95, 10),
        ]
    )
    df = pd.DataFrame(
        {
            "date": dates,
            "open": prices - 0.3,
            "high": prices + 0.5,
            "low": prices - 0.5,
            "close": prices,
            "volume": np.random.uniform(1e6, 1e8, 30).astype(int),
        }
    )
    df["pct_change"] = df["close"].pct_change() * 100
    return df
