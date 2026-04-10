"""依赖可用性检查"""

# 数据请求库
try:
    import requests  # noqa: F401

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# A股数据源
try:
    import akshare as ak  # noqa: F401

    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

# 美股/港股数据源
try:
    import yfinance as yf  # noqa: F401

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def check_dependencies() -> dict:
    """返回所有依赖的可用状态"""
    return {
        "requests": REQUESTS_AVAILABLE,
        "akshare": AKSHARE_AVAILABLE,
        "yfinance": YFINANCE_AVAILABLE,
    }


def get_available_data_sources() -> list:
    """返回可用的数据源列表"""
    sources = []
    if REQUESTS_AVAILABLE:
        sources.append("sina")
    if AKSHARE_AVAILABLE:
        sources.append("akshare")
    if YFINANCE_AVAILABLE:
        sources.append("yfinance")
    return sources
