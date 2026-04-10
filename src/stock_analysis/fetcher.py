"""股票技术分析工具 - 数据获取器"""

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd

from .dependencies import AKSHARE_AVAILABLE, REQUESTS_AVAILABLE, YFINANCE_AVAILABLE

logger = logging.getLogger("stock_analysis.fetcher")

from .constants import AUTO_FUND_PREFIXES, ETF_PREFIXES, LOF_PREFIXES, SH_PREFIXES  # noqa: E402


class StockDataFetcher:
    """多数据源股票/基金数据获取器"""

    # -------------------- 代码标准化 --------------------

    @staticmethod
    def normalize_stock_code(code: str, market: str = "auto", asset_type: str = "stock") -> Tuple[str, str, str]:
        """
        标准化证券代码，自动识别市场和资产类型。

        Returns:
            (标准代码, 市场, 资产类型)
        """
        code = code.strip().upper()

        # 港股识别（优先于基金，因为 00700 等以 00 开头）
        if code.startswith("HK.") or code.startswith("港."):
            clean = code.replace("HK.", "").replace("港.", "")
            return clean, "hkstock", "stock"

        # 基金识别：仅高置信度前缀（ETF/LOF）自动识别，开放式基金需 -t fund 指定
        if asset_type == "fund" or (len(code) == 6 and code.isdigit() and code.startswith(AUTO_FUND_PREFIXES)):
            return code, "ashare", "fund"

        # 美股识别：含市场标识或纯字母
        if any(k in code for k in ("US", "NASDAQ", "NYSE", "AMEX")) or (code.isalpha() and len(code) > 1):
            clean = code.replace("US.", "").replace("NASDAQ:", "").replace("NYSE:", "").replace("AMEX:", "")
            return clean, "usstock", "stock"

        # 指定市场
        if market != "auto":
            return code, market, asset_type

        # A股默认
        if len(code) == 6 and code.isdigit():
            return code, "ashare", "stock"

        return code, "ashare", "stock"

    # -------------------- 新浪数据源（A股） --------------------

    @staticmethod
    def _build_sina_symbol(code: str) -> str:
        """构建新浪证券代码"""
        return f"sh{code}" if code.startswith(SH_PREFIXES) else f"sz{code}"

    @staticmethod
    def fetch_stock_data_sina(code: str, market: str, days: int = 60) -> Optional[pd.DataFrame]:
        """通过新浪接口获取A股历史K线数据（带2次重试）"""
        if market != "ashare" or not REQUESTS_AVAILABLE:
            return None

        for attempt in range(3):
            try:
                symbol = StockDataFetcher._build_sina_symbol(code)
                url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
                params = {"symbol": symbol, "scale": "240", "ma": "no", "datalen": days}

                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()

                if not data or not isinstance(data, list):
                    return None

                records = []
                for item in data:
                    records.append(
                        {
                            "date": pd.to_datetime(item.get("day", "")),
                            "open": pd.to_numeric(item.get("open", 0), errors="coerce"),
                            "high": pd.to_numeric(item.get("high", 0), errors="coerce"),
                            "low": pd.to_numeric(item.get("low", 0), errors="coerce"),
                            "close": pd.to_numeric(item.get("close", 0), errors="coerce"),
                            "volume": pd.to_numeric(item.get("volume", 0), errors="coerce"),
                            "amount": pd.to_numeric(item.get("amount", 0), errors="coerce"),
                        }
                    )

                df = pd.DataFrame(records)
                if df.empty:
                    return None

                df["pct_change"] = df["close"].pct_change() * 100
                df = df.sort_values("date").reset_index(drop=True)
                return df

            except Exception as e:
                logger.warning("新浪历史数据第%d次尝试失败 [%s]: %s", attempt + 1, code, e)
                if attempt < 2:
                    time.sleep(1)

        return None

    @staticmethod
    def fetch_realtime_quote_sina(code: str, market: str) -> Optional[Dict]:
        """通过新浪接口获取A股实时行情"""
        if market != "ashare" or not REQUESTS_AVAILABLE:
            return None

        try:
            symbol = StockDataFetcher._build_sina_symbol(code)
            url = f"https://hq.sinajs.cn/list={symbol}"
            headers = {"Referer": "https://finance.sina.com.cn"}

            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            resp.encoding = "gbk"

            match = re.search(r'="(.+)"', resp.text)
            if not match:
                return None

            parts = match.group(1).split(",")
            if len(parts) < 32:
                return None

            name = parts[0]
            open_price = float(parts[1]) if parts[1] else 0
            prev_close = float(parts[2]) if parts[2] else 0
            current = float(parts[3]) if parts[3] else 0
            high = float(parts[4]) if parts[4] else 0
            low = float(parts[5]) if parts[5] else 0
            volume = float(parts[8]) if parts[8] else 0
            amount = float(parts[9]) if parts[9] else 0

            pct_change = ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0

            return {
                "name": name,
                "price": current,
                "change": round(current - prev_close, 4),
                "pct_change": round(pct_change, 2),
                "open": open_price,
                "high": high,
                "low": low,
                "prev_close": prev_close,
                "volume": volume,
                "amount": amount,
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        except Exception as e:
            logger.warning("新浪实时行情失败 [%s]: %s", code, e)
            return None

    # -------------------- yfinance 数据源（港美股） --------------------

    @staticmethod
    def _build_yfinance_code(code: str, market: str) -> Optional[str]:
        """构建 yfinance 代码格式"""
        if market == "hkstock":
            return f"{code.zfill(4)}.HK"
        elif market == "usstock":
            return code
        return None

    @staticmethod
    def fetch_stock_data_yfinance(code: str, market: str, days: int = 60) -> Optional[pd.DataFrame]:
        """通过 yfinance 获取港美股历史数据（带2次重试）"""
        if not YFINANCE_AVAILABLE:
            return None

        for attempt in range(3):
            try:
                yf_code = StockDataFetcher._build_yfinance_code(code, market)
                if yf_code is None:
                    return None

                ticker = yf.Ticker(yf_code)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days * 2)

                df = ticker.history(start=start_date, end=end_date, period=None)
                if df.empty:
                    return None

                df = df.reset_index()
                df = df.rename(
                    columns={
                        "Date": "date",
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume",
                    }
                )
                # 补充 amount 列（yfinance 无成交额，用 0 填充）
                df["amount"] = 0
                df["pct_change"] = df["close"].pct_change() * 100
                df = df.sort_values("date").reset_index(drop=True)
                return df

            except Exception as e:
                logger.warning("yfinance历史数据第%d次尝试失败 [%s]: %s", attempt + 1, code, e)
                if attempt < 2:
                    time.sleep(2)

        return None

    @staticmethod
    def fetch_realtime_quote_yfinance(code: str, market: str) -> Optional[Dict]:
        """通过 yfinance 获取港美股实时行情"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            yf_code = StockDataFetcher._build_yfinance_code(code, market)
            if yf_code is None:
                return None

            ticker = yf.Ticker(yf_code)
            info = ticker.info

            return {
                "name": info.get("shortName", code),
                "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "change": info.get("regularMarketChange", 0),
                "pct_change": (
                    round(info.get("regularMarketChangePercent", 0) * 100, 2)
                    if info.get("regularMarketChangePercent")
                    else 0
                ),
                "open": info.get("regularMarketOpen", info.get("open", 0)),
                "high": info.get("dayHigh", 0),
                "low": info.get("dayLow", 0),
                "prev_close": info.get("regularMarketPreviousClose", info.get("previousClose", 0)),
                "volume": info.get("volume", 0),
                "amount": 0,
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        except Exception as e:
            logger.warning("yfinance实时行情失败 [%s]: %s", code, e)
            return None

    # -------------------- akshare 数据源（通用备用） --------------------

    @staticmethod
    def fetch_stock_data_akshare(code: str, market: str, days: int = 60) -> Optional[pd.DataFrame]:
        """通过 akshare 获取股票数据（带3次重试）"""
        if not AKSHARE_AVAILABLE:
            return None

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        df = None

        for attempt in range(3):
            df = None  # 每次重试前重置，避免返回脏数据
            try:
                if market == "usstock":
                    df = ak.stock_us_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="",
                    )
                elif market == "hkstock":
                    df = ak.stock_hk_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="",
                    )
                else:
                    df = ak.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="",
                    )

                if df is not None and not df.empty:
                    df = df.rename(
                        columns={
                            "日期": "date",
                            "开盘": "open",
                            "收盘": "close",
                            "最高": "high",
                            "最低": "low",
                            "成交量": "volume",
                            "成交额": "amount",
                            "涨跌幅": "pct_change",
                        }
                    )
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").reset_index(drop=True)
                    return df

            except Exception as e:
                logger.warning("akshare第%d次尝试失败 [%s]: %s", attempt + 1, code, e)
                time.sleep(2)

        return df

    @staticmethod
    def fetch_realtime_quote_akshare(code: str, market: str) -> Optional[Dict]:
        """通过 akshare 获取实时行情"""
        if not AKSHARE_AVAILABLE:
            return None

        try:
            if market == "usstock":
                df = ak.stock_us_spot_em()
                row = df[df["代码"] == code]
                if row.empty:
                    row = df[df["名称"].str.contains(code, case=False, na=False)]
            elif market == "hkstock":
                df = ak.stock_hk_spot_em()
                row = df[df["代码"] == code]
            else:
                df = ak.stock_zh_a_spot_em()
                row = df[df["代码"] == code]

            if row.empty:
                return None

            row = row.iloc[0]
            return {
                "name": str(row.get("名称", code)),
                "price": float(row.get("最新价", 0)),
                "change": float(row.get("涨跌额", 0)),
                "pct_change": float(row.get("涨跌幅", 0)),
                "high": float(row.get("最高", 0)),
                "low": float(row.get("最低", 0)),
                "volume": float(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "time": str(row.get("时间", "")),
            }

        except Exception as e:
            logger.warning("akshare实时行情失败 [%s]: %s", code, e)
            return None

    # -------------------- 东财直接API（基金备用） --------------------

    @staticmethod
    def fetch_fund_data_eastmoney_direct(
        code: str, start_date: str, end_date: str, days: int = 60
    ) -> Optional[pd.DataFrame]:
        """直接调用东财基金历史API（绕过akshare）"""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            url = "https://api.fund.eastmoney.com/f10/lsjz"
            params = {
                "fundCode": code,
                "pageIndex": 1,
                "pageSize": 120,
                "startDate": start_date,
                "endDate": end_date,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://fund.eastmoney.com/",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.encoding = "utf-8"

            match = re.search(r"\{.*\}", resp.text.strip(), re.DOTALL)
            if not match:
                return None

            data = json.loads(match.group())
            records = data.get("Data", {}).get("LSJZList", [])
            if not records:
                return None

            rows = []
            for rec in records:
                nav = float(rec.get("DWJZ", 0))
                rows.append(
                    {
                        "date": pd.to_datetime(rec.get("FSRQ", "")),
                        "open": nav,
                        "high": nav,
                        "low": nav,
                        "close": nav,
                        "volume": 0,
                        "pct_change": float(rec.get("JZZZL", 0)) if rec.get("JZZZL") else 0,
                    }
                )

            df = pd.DataFrame(rows)
            df = df.sort_values("date").reset_index(drop=True)
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)
            return df

        except Exception as e:
            logger.warning("东财基金直接API失败 [%s]: %s", code, e)
            return None

    # -------------------- 基金数据源 --------------------

    @staticmethod
    def get_fund_type(code: str) -> str:
        """
        判断基金类型。

        Returns:
            'etf' | 'lof' | 'open'
        """
        if code.startswith(ETF_PREFIXES):
            return "etf"
        elif code.startswith(LOF_PREFIXES):
            return "lof"
        return "open"

    @staticmethod
    def fetch_fund_data_akshare(code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """通过 akshare 获取基金净值数据（多级回退）"""
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare未安装，无法获取基金数据 [%s]", code)
            return None

        fund_type = StockDataFetcher.get_fund_type(code)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        df = None

        if fund_type in ("etf", "lof"):
            df = StockDataFetcher._fetch_fund_etf_lof(code, fund_type, days, start_date, end_date)
        else:
            df = StockDataFetcher._fetch_fund_open(code, days, start_date, end_date)

        if df is None or df.empty:
            logger.warning("基金 %s 数据获取失败", code)
            return None

        # 统一后处理
        df["date"] = pd.to_datetime(df["date"])
        if "pct_change" in df.columns:
            df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)
        if len(df) > days:
            df = df.tail(days).reset_index(drop=True)

        return df

    @staticmethod
    def _fetch_fund_etf_lof(
        code: str, fund_type: str, days: int, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """获取 ETF/LOF 基金数据（新浪 → 东财akshare → 东财直接API）"""
        logger.info("获取ETF/LOF数据: %s (类型: %s)", code, fund_type)
        df = None

        # 1. 尝试新浪ETF接口
        try:
            sina_symbol = StockDataFetcher._build_sina_symbol(code)
            df = ak.fund.fund_etf_sina.fund_etf_hist_sina(symbol=sina_symbol)
            if df is not None and not df.empty:
                df = df.rename(
                    columns={
                        "date": "date",
                        "open": "open",
                        "close": "close",
                        "high": "high",
                        "low": "low",
                        "volume": "volume",
                        "amount": "amount",
                    }
                )
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                if len(df) > days:
                    df = df.tail(days).reset_index(drop=True)
                return df
        except Exception as e:
            logger.warning("新浪ETF接口失败，回退东财: %s", e)

        # 2. 东财 akshare 接口
        try:
            if fund_type == "etf":
                df = ak.fund_etf_hist_em(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                )
            else:
                df = ak.fund.fund_lof_em.fund_lof_hist_em(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                )
            if df is not None and not df.empty:
                df = df.rename(
                    columns={
                        "日期": "date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "volume",
                        "成交额": "amount",
                        "涨跌幅": "pct_change",
                    }
                )
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                return df
        except Exception as e:
            logger.warning("东财akshare ETF/LOF接口失败: %s", e)
            df = None

        # 3. 东财直接API
        df2 = StockDataFetcher.fetch_fund_data_eastmoney_direct(code, start_date, end_date, days)
        if df2 is not None and not df2.empty:
            return df2

        return None

    @staticmethod
    def _fetch_fund_open(code: str, days: int, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取开放式基金数据（fund_open_fund_info_em → 东财直接API → LOF回退）"""
        logger.info("获取开放式基金数据: %s", code)
        df = None

        # 1. fund_open_fund_info_em
        try:
            df = ak.fund.fund_em.fund_open_fund_info_em(
                symbol=code,
                indicator="单位净值走势",
                period="近1年",
            )
            if df is not None and not df.empty:
                df = df.rename(
                    columns={
                        "净值日期": "date",
                        "单位净值": "close",
                        "日增长率": "pct_change",
                    }
                )
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["open"] = df["close"]
                df["high"] = df["close"]
                df["low"] = df["close"]
                df["volume"] = 0
                df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
                if len(df) > days:
                    df = df.tail(days).reset_index(drop=True)
                return df
        except Exception as e:
            logger.warning("fund_open_fund_info_em 失败: %s", e)
            df = None

        # 2. 东财直接API
        df2 = StockDataFetcher.fetch_fund_data_eastmoney_direct(code, start_date, end_date, days)
        if df2 is not None and not df2.empty:
            return df2

        # 3. LOF 历史接口（最后回退）
        try:
            df = ak.fund.fund_lof_em.fund_lof_hist_em(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
            if df is not None and not df.empty:
                df = df.rename(
                    columns={
                        "日期": "date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "volume",
                        "成交额": "amount",
                        "涨跌幅": "pct_change",
                    }
                )
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                return df
        except Exception as e:
            logger.warning("LOF备用接口也失败: %s", e)

        return None

    @staticmethod
    def fetch_fund_info_akshare(code: str) -> Optional[Dict]:
        """获取基金基本信息"""
        fund_type = StockDataFetcher.get_fund_type(code)

        # ETF：优先新浪实时接口
        if fund_type == "etf" and REQUESTS_AVAILABLE:
            try:
                sina_sym = StockDataFetcher._build_sina_symbol(code)
                url = f"https://hq.sinajs.cn/list={sina_sym}"
                headers = {"Referer": "https://finance.sina.com.cn"}
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                resp.encoding = "gbk"
                match = re.search(r'="(.+)"', resp.text)
                if not match:
                    return None
                parts = match.group(1).split(",")
                if len(parts) > 3:
                    return {
                        "name": parts[0],
                        "type": "ETF",
                        "price": float(parts[3]) if parts[3] else 0,
                    }
            except Exception as e:
                logger.warning("新浪ETF信息失败: %s", e)

        # ETF/LOF：东财实时列表
        if fund_type in ("etf", "lof") and AKSHARE_AVAILABLE:
            try:
                if fund_type == "etf":
                    df = ak.fund_etf_spot_em()
                else:
                    df = ak.fund.fund_lof_em.fund_lof_spot_em()
                row = df[df["代码"] == code]
                if not row.empty:
                    row = row.iloc[0]
                    return {
                        "name": str(row.get("名称", code)),
                        "type": fund_type.upper(),
                        "price": float(row.get("最新价", 0)),
                    }
                # ETF/LOF 实时列表未找到，尝试基金名称搜索
                try:
                    name_df = ak.fund_name_em()
                    row = name_df[name_df["基金代码"] == code]
                    if not row.empty:
                        return {
                            "name": str(row.iloc[0].get("基金简称", code)),
                            "type": fund_type.upper(),
                            "price": 0,
                        }
                except Exception:
                    pass
            except Exception as e:
                logger.warning("东财基金信息失败: %s", e)

        # 开放式基金：通过东财API获取基金名称
        if fund_type == "open" and AKSHARE_AVAILABLE:
            try:
                df = ak.fund.fund_em.fund_open_fund_info_em(
                    symbol=code,
                    indicator="单位净值走势",
                )
                if df is not None and not df.empty:
                    # 尝试从 akshare 基金名称搜索接口获取名称
                    try:
                        name_df = ak.fund_name_em()
                        row = name_df[name_df["基金代码"] == code]
                        if not row.empty:
                            fund_name = str(row.iloc[0].get("基金简称", code))
                        else:
                            fund_name = code
                    except Exception:
                        fund_name = code
                    return {"name": fund_name, "type": "开放式基金"}
            except Exception as e:
                logger.warning("开放式基金信息失败: %s", e)

        return {"name": code, "type": fund_type.upper()}

    # -------------------- 统一入口 --------------------

    @staticmethod
    def fetch_data(code: str, market: str, asset_type: str, days: int = 60, total_timeout: float = 60.0) -> Optional[pd.DataFrame]:
        """获取历史数据统一入口

        Args:
            total_timeout: 整个 fallback 链的总超时（秒），默认 60 秒
        """
        import threading

        result_holder: list = [None]
        error_holder: list = [None]

        def _do_fetch():
            try:
                if asset_type == "fund":
                    result_holder[0] = StockDataFetcher.fetch_fund_data_akshare(code, days)
                    return

                if market == "ashare":
                    df = StockDataFetcher.fetch_stock_data_sina(code, market, days)
                    if df is not None:
                        result_holder[0] = df
                        return
                    logger.info("新浪失败，尝试akshare备用...")
                    result_holder[0] = StockDataFetcher.fetch_stock_data_akshare(code, market, days)
                    return

                # 港美股：yfinance → akshare
                df = StockDataFetcher.fetch_stock_data_yfinance(code, market, days)
                if df is not None:
                    result_holder[0] = df
                    return
                logger.info("yfinance失败，尝试akshare备用...")
                result_holder[0] = StockDataFetcher.fetch_stock_data_akshare(code, market, days)
            except Exception as e:
                error_holder[0] = e

        t = threading.Thread(target=_do_fetch)
        t.start()
        t.join(timeout=total_timeout)

        if t.is_alive():
            logger.warning("获取数据超时 (%.0fs): %s %s", total_timeout, code, market)
            return None

        if error_holder[0] is not None:
            logger.warning("获取数据异常: %s %s: %s", code, market, error_holder[0])

        return result_holder[0]

    @staticmethod
    def fetch_quote(code: str, market: str, asset_type: str) -> Optional[Dict]:
        """获取实时行情统一入口"""
        if asset_type == "fund":
            info = StockDataFetcher.fetch_fund_info_akshare(code)
            return info if info else None

        if market == "ashare":
            quote = StockDataFetcher.fetch_realtime_quote_sina(code, market)
            if quote:
                return quote
            return StockDataFetcher.fetch_realtime_quote_akshare(code, market)

        # 港美股
        quote = StockDataFetcher.fetch_realtime_quote_yfinance(code, market)
        if quote:
            return quote
        return StockDataFetcher.fetch_realtime_quote_akshare(code, market)
