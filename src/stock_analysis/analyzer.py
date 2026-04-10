"""股票技术分析工具 - 综合分析器"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .fetcher import REQUESTS_AVAILABLE, YFINANCE_AVAILABLE, StockDataFetcher
from .indicators import TechnicalIndicators
from .scorer import Scorer
from .support import SupportResistanceFinder

logger = logging.getLogger("stock_analysis.analyzer")


class StockAnalyzer:
    """股票综合分析器"""

    def __init__(self):
        self.data_fetcher = StockDataFetcher()
        self.indicators = TechnicalIndicators()
        self.levels_finder = SupportResistanceFinder()
        # 数据缓存，格式: { (code, market, asset_type, days): (timestamp, df) }
        self._data_cache = {}
        # 缓存有效期：5分钟
        self._cache_expiry = 300

    def analyze(
        self,
        code: str,
        market: str = "auto",
        asset_type: str = "stock",
        days: int = 60,
        return_df: bool = False,
    ) -> Dict[str, Any]:
        """执行完整的技术分析

        Args:
            return_df: 如果为 True，返回结果中包含 '_df' 键（原始 DataFrame），避免二次获取
        """
        code, market, asset_type = self.data_fetcher.normalize_stock_code(code, market, asset_type)
        logger.info("分析: %s (市场: %s, 类型: %s)", code, market, asset_type)

        # 检查缓存
        cache_key = (code, market, asset_type, days)
        import time
        current_time = time.time()
        
        if cache_key in self._data_cache:
            cached_time, cached_df = self._data_cache[cache_key]
            if current_time - cached_time < self._cache_expiry:
                logger.info("使用缓存数据: %s", code)
                df = cached_df
            else:
                logger.info("缓存过期，重新获取数据: %s", code)
                df = self.data_fetcher.fetch_data(code, market, asset_type, days)
                if df is not None and not df.empty:
                    self._data_cache[cache_key] = (current_time, df)
        else:
            logger.info("缓存未命中，获取新数据: %s", code)
            df = self.data_fetcher.fetch_data(code, market, asset_type, days)
            if df is not None and not df.empty:
                self._data_cache[cache_key] = (current_time, df)
        
        if df is None or df.empty:
            # 区分网络问题和数据不存在
            error_msg = f"无法获取 {code} 的数据"
            if not REQUESTS_AVAILABLE and market == "ashare":
                error_msg = f"无法获取 {code} 的数据（requests 未安装，请运行: pip install requests）"
            elif not YFINANCE_AVAILABLE and market in ("hkstock", "usstock"):
                error_msg = f"无法获取 {code} 的数据（yfinance 未安装，请运行: pip install yfinance）"
            return {
                "error": error_msg,
                "stock_info": {"code": code, "market": market, "asset_type": asset_type},
            }

        logger.info("获取到 %d 条历史数据", len(df))

        quote = self.data_fetcher.fetch_quote(code, market, asset_type)

        # 基础信息
        change_pct = 0
        if "pct_change" in df.columns and pd.notna(df["pct_change"].iloc[-1]):
            change_pct = round(float(df["pct_change"].iloc[-1]), 2)

        stock_info = {
            "code": code,
            "name": quote.get("name", code) if quote else code,
            "market": market,
            "asset_type": asset_type,
            "current_price": round(float(df["close"].iloc[-1]), 4),
            "change_pct": change_pct,
            "update_time": df["date"].iloc[-1].strftime("%Y-%m-%d"),
        }

        # 实时行情覆盖
        if quote and quote.get("price"):
            stock_info["current_price"] = quote["price"]
            stock_info["change_pct"] = quote.get("pct_change", change_pct)
            stock_info["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 计算技术指标
        ma = self.indicators.calculate_ma(df)
        macd = self.indicators.calculate_macd(df)
        rsi = self.indicators.calculate_rsi(df)
        bollinger = self.indicators.calculate_bollinger(df)
        kdj = self.indicators.calculate_kdj(df)
        atr = self.indicators.calculate_atr(df)
        volume = self.indicators.calculate_volume(df)

        # 布林带收窄检测
        if bollinger.get("bb_width") and len(df) >= 20:
            bbw_series = (df["close"].rolling(20).std() * 4) / df["close"].rolling(20).mean() * 100
            if pd.notna(bbw_series.iloc[-1]) and len(bbw_series.dropna()) >= 20:
                bollinger["squeeze"] = bool(bbw_series.iloc[-1] <= bbw_series.iloc[-20:].min() * 1.1)

        # 支撑压力位（基金类型跳过无意义的计算）
        levels = self.levels_finder.find_levels(df, asset_type=asset_type)

        # 综合评分
        score, trend, recommendation = Scorer.calculate_score(df, ma, macd, rsi, bollinger, kdj=kdj, volume=volume)

        result = {
            "stock_info": stock_info,
            "technical_indicators": {
                "ma": ma,
                "macd": macd,
                "rsi": rsi,
                "bollinger": bollinger,
                "kdj": kdj,
                "atr": atr,
                "volume_analysis": volume,
            },
            "key_levels": levels,
            "analysis": {
                "score": score,
                "trend": trend,
                "recommendation": recommendation,
                "summary": self._generate_summary(stock_info, ma, macd, rsi, bollinger, score, kdj=kdj, volume=volume),
            },
        }

        if return_df:
            result["_df"] = df

        return result

    def analyze_batch(
        self,
        codes: List[str],
        market: str = "auto",
        test: bool = False,
        asset_type: str = "stock",
        days: int = 60,
    ) -> Dict[str, Any]:
        """批量分析多只股票/基金（并发请求）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _analyze_one(item: str) -> Dict:
            actual_type = asset_type
            if ":" in item:
                code, actual_type = item.split(":", 1)
                code = code.strip()
                actual_type = actual_type.strip()
            else:
                code = item.strip()

            if test:
                return self.analyze_with_mock_data(code, market, actual_type)
            else:
                return self.analyze(code, market, actual_type, days)

        results = []
        # 并发执行，最多5个线程
        max_workers = min(5, len(codes))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_analyze_one, item): item for item in codes}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    item = futures[future]
                    code = item.split(":")[0].strip() if ":" in item else item.strip()
                    results.append({"error": str(e), "stock_info": {"code": code}})

        # 汇总统计
        summary = {"强势上涨": 0, "上涨趋势": 0, "震荡整理": 0, "下跌趋势": 0, "强势下跌": 0}
        total_score = 0
        valid_count = 0
        failed: List[Dict] = []

        for result in results:
            if "analysis" in result:
                trend = result["analysis"]["trend"]
                if trend in summary:
                    summary[trend] += 1
                total_score += result["analysis"]["score"]
                valid_count += 1
            elif "error" in result:
                failed.append(
                    {
                        "code": result.get("stock_info", {}).get("code", "?"),
                        "error": result["error"],
                    }
                )

        # 失败项自动重试一轮
        if failed and not test:
            retry_codes = [f["code"] for f in failed]
            logger.info("批量分析有 %d 项失败，自动重试: %s", len(retry_codes), ", ".join(retry_codes))
            retry_results = []
            max_workers = min(5, len(retry_codes))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_analyze_one, item): item for item in retry_codes}
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=90)
                        retry_results.append(result)
                    except Exception as e:
                        item = futures[future]
                        code = item.split(":")[0].strip() if ":" in item else item.strip()
                        retry_results.append({"error": str(e), "stock_info": {"code": code}})

            # 合并重试结果：成功的替换原失败项
            new_failed = []
            for retry_result in retry_results:
                if "analysis" in retry_result:
                    trend = retry_result["analysis"]["trend"]
                    if trend in summary:
                        summary[trend] += 1
                    total_score += retry_result["analysis"]["score"]
                    valid_count += 1
                    # 替换原 results 中的失败项
                    retry_code = retry_result.get("stock_info", {}).get("code", "")
                    for i, r in enumerate(results):
                        if r.get("error") and r.get("stock_info", {}).get("code") == retry_code:
                            results[i] = retry_result
                            break
                else:
                    new_failed.append(
                        {
                            "code": retry_result.get("stock_info", {}).get("code", "?"),
                            "error": retry_result["error"],
                        }
                    )
            failed = new_failed

        avg_score = round(total_score / valid_count, 1) if valid_count > 0 else 0

        return {
            "results": results,
            "summary": {
                **summary,
                "total": len(codes),
                "valid": valid_count,
                "failed_count": len(failed),
                "avg_score": avg_score,
            },
            "failed": failed if failed else None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def analyze_with_mock_data(
        self,
        code: str,
        market: str = "auto",
        asset_type: str = "stock",
        days: int = 60,
        return_df: bool = False,
    ) -> Dict[str, Any]:
        """使用模拟数据进行离线测试（无需网络）"""
        # test 模式跳过 normalize（会触发网络请求），直接使用传入参数
        effective_market = market if market != "auto" else "ashare"
        effective_asset = asset_type
        code = code.strip()
        logger.info("[TEST] 模拟数据: %s (市场: %s, 类型: %s, 天数: %d)", code, effective_market, effective_asset, days)

        np.random.seed(hash(code) % 2**32)
        base_price = np.random.uniform(10, 2000)

        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
        trend = np.random.uniform(-0.002, 0.003)
        returns = np.random.normal(trend, 0.02, days)
        prices = base_price * np.cumprod(1 + returns)

        df = pd.DataFrame(
            {
                "date": dates,
                "open": prices * np.random.uniform(0.98, 1.02, days),
                "high": prices * np.random.uniform(1.0, 1.05, days),
                "low": prices * np.random.uniform(0.95, 1.0, days),
                "close": prices,
                "volume": np.random.uniform(1e6, 1e8, days).astype(int),
            }
        )
        df["pct_change"] = df["close"].pct_change() * 100

        name_map = {
            "600519": "贵州茅台",
            "000001": "平安银行",
            "000858": "五粮液",
            "00700": "腾讯控股",
            "AAPL": "苹果",
            "TSLA": "特斯拉",
            "001316": "安信稳健增值",
            "000369": "国泰金龙行业",
        }

        stock_info = {
            "code": code,
            "name": name_map.get(code, f"标的{code}"),
            "market": effective_market,
            "asset_type": effective_asset,
            "current_price": round(float(prices[-1]), 4),
            "change_pct": round(float(df["pct_change"].iloc[-1]), 2),
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_mock_data": True,
        }

        ma = self.indicators.calculate_ma(df)
        macd = self.indicators.calculate_macd(df)
        rsi = self.indicators.calculate_rsi(df)
        bollinger = self.indicators.calculate_bollinger(df)
        kdj = self.indicators.calculate_kdj(df)
        atr = self.indicators.calculate_atr(df)
        volume = self.indicators.calculate_volume(df)

        levels = self.levels_finder.find_levels(df, asset_type=asset_type)
        score, trend, recommendation = Scorer.calculate_score(df, ma, macd, rsi, bollinger, kdj=kdj, volume=volume)

        result = {
            "stock_info": stock_info,
            "technical_indicators": {
                "ma": ma,
                "macd": macd,
                "rsi": rsi,
                "bollinger": bollinger,
                "kdj": kdj,
                "atr": atr,
                "volume_analysis": volume,
            },
            "key_levels": levels,
            "analysis": {
                "score": score,
                "trend": trend,
                "recommendation": recommendation,
                "summary": self._generate_summary(stock_info, ma, macd, rsi, bollinger, score, kdj=kdj, volume=volume),
            },
        }
        if return_df:
            result["_df"] = df
        return result

    @staticmethod
    def _generate_summary(
        stock_info: Dict,
        ma: Dict,
        macd: Dict,
        rsi: Dict,
        bollinger: Dict,
        score: int,
        kdj: Optional[Dict] = None,
        volume: Optional[Dict] = None,
    ) -> str:
        """生成中文分析摘要"""
        parts = []

        price = stock_info.get("current_price", 0)
        change = stock_info.get("change_pct", 0)
        name = stock_info.get("name", "")
        asset_type = stock_info.get("asset_type", "stock")

        price_label = "净值" if asset_type == "fund" else "现价"
        direction = "上涨" if change >= 0 else "下跌"
        parts.append(f"{name}{price_label}{price}，{direction}{abs(change):.2f}%")

        if ma.get("MA5") and ma.get("MA20"):
            ma_status = "多头" if ma["MA5"] > ma["MA20"] else "空头"
            parts.append(f"均线{ma_status}排列")

        if macd.get("signal") and macd["signal"] != "中性":
            parts.append(f"MACD{macd['signal']}")

        rsi_val = rsi.get("RSI12")
        if rsi_val is not None:
            if rsi_val > 70:
                parts.append(f"RSI超买({rsi_val:.0f})")
            elif rsi_val < 30:
                parts.append(f"RSI超卖({rsi_val:.0f})")

        if bollinger.get("position") and bollinger["position"] != "中位":
            parts.append(f"布林{bollinger['position']}")

        if bollinger.get("squeeze"):
            parts.append("布林收窄")

        if kdj and kdj.get("signal") and kdj["signal"] in ("超买", "超卖"):
            parts.append(f"KDJ{kdj['signal']}")

        if (
            volume
            and volume.get("volume_signal")
            and volume["volume_signal"] not in ("正常", "数据不足", "无成交量数据")
        ):
            parts.append(volume["volume_signal"])

        parts.append(f"评分{score}")

        return "；".join(parts)
