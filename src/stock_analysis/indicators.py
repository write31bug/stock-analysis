"""股票技术指标计算模块"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("stock_analysis.indicators")


class TechnicalIndicators:
    """股票技术指标计算器"""

    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: Optional[List[int]] = None) -> Dict[str, Optional[float]]:
        """计算移动平均线 (MA)"""
        if periods is None:
            periods = [5, 10, 20, 60]

        result = {}
        for period in periods:
            if len(df) >= period:
                ma = df["close"].rolling(window=period).mean().iloc[-1]
                result[f"MA{period}"] = round(float(ma), 4)
            else:
                result[f"MA{period}"] = None
        return result

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
        """计算 MACD 指标"""
        if len(df) < slow:
            return {"DIF": None, "DEA": None, "MACD": None, "signal": "数据不足"}

        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = (dif - dea) * 2

        dif_val = dif.iloc[-1]
        dea_val = dea.iloc[-1]
        macd_val = macd_hist.iloc[-1]

        # 金叉/死叉信号
        if len(dif) >= 2:
            prev_dif, prev_dea = dif.iloc[-2], dea.iloc[-2]
            if prev_dif <= prev_dea and dif_val > dea_val:
                sig = "金叉"
            elif prev_dif >= prev_dea and dif_val < dea_val:
                sig = "死叉"
            else:
                sig = "中性"
        else:
            sig = "中性"

        # 背离检测（最近20个交易日内）
        divergence = "无"
        lookback = min(20, len(df) - 1)
        if lookback >= 10:
            prices = df["close"].iloc[-lookback:]
            dif_series = dif.iloc[-lookback:]

            # 找价格局部高点（顶背离）
            price_highs_idx = []
            for i in range(2, len(prices) - 2):
                if (
                    prices.iloc[i] >= prices.iloc[i - 1]
                    and prices.iloc[i] >= prices.iloc[i - 2]
                    and prices.iloc[i] >= prices.iloc[i + 1]
                    and prices.iloc[i] >= prices.iloc[i + 2]
                ):
                    price_highs_idx.append(i)

            if len(price_highs_idx) >= 2:
                last_two = price_highs_idx[-2:]
                p1, p2 = prices.iloc[last_two[0]], prices.iloc[last_two[1]]
                d1, d2 = dif_series.iloc[last_two[0]], dif_series.iloc[last_two[1]]
                if p2 > p1 and d2 < d1:
                    divergence = "顶背离"
                elif p2 < p1 and d2 > d1:
                    divergence = "底背离"

        return {
            "DIF": round(float(dif_val), 4),
            "DEA": round(float(dea_val), 4),
            "MACD": round(float(macd_val), 4),
            "signal": sig,
            "divergence": divergence,
        }

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, periods: Optional[List[int]] = None) -> Dict[str, Optional[float]]:
        """计算 RSI 相对强弱指数"""
        if periods is None:
            periods = [6, 12, 24]

        result = {}
        delta = df["close"].diff()

        for period in periods:
            if len(df) < period:
                result[f"RSI{period}"] = None
                continue

            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            # 避免除零，NaN 转为 None
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            val = rsi.iloc[-1]
            result[f"RSI{period}"] = round(float(val), 2) if pd.notna(val) else None

        return result

    @staticmethod
    def calculate_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
        """计算布林带 (BOLL)"""
        if len(df) < period:
            return {"upper": None, "middle": None, "lower": None, "position": "数据不足", "bb_position": None}

        middle = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()

        upper = middle + std_dev * std
        lower = middle - std_dev * std

        current_price = df["close"].iloc[-1]
        upper_val = upper.iloc[-1]
        middle_val = middle.iloc[-1]
        lower_val = lower.iloc[-1]

        # NaN 安全检查
        if pd.isna(upper_val) or pd.isna(lower_val) or pd.isna(middle_val) or pd.isna(current_price):
            return {"upper": None, "middle": None, "lower": None, "position": "数据不足", "bb_position": None}

        # 价格在布林带中的位置百分比 (0~1)
        bb_width = upper_val - lower_val
        bb_position = (current_price - lower_val) / bb_width if bb_width > 0 else 0.5

        # 位置判断
        if current_price > upper_val:
            position = "突破上轨"
        elif current_price >= middle_val:
            position = "高位"
        elif current_price >= lower_val:
            position = "中位"
        else:
            position = "突破下轨"

        return {
            "upper": round(float(upper_val), 4),
            "middle": round(float(middle_val), 4),
            "lower": round(float(lower_val), 4),
            "position": position,
            "bb_position": round(float(bb_position), 2),
            "bb_width": round(float(bb_width / middle_val * 100), 2) if middle_val > 0 else 0,
            "squeeze": False,
        }

    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Dict[str, Any]:
        """计算 KDJ 随机指标"""
        if len(df) < n:
            return {"K": None, "D": None, "J": None, "signal": "数据不足"}

        low_list = df["low"].rolling(window=n, min_periods=1).min()
        high_list = df["high"].rolling(window=n, min_periods=1).max()
        # 避免除零错误
        range_list = high_list - low_list
        rsv = np.where(range_list > 0, (df["close"] - low_list) / range_list * 100, 50)
        rsv = pd.Series(rsv, index=df.index)

        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d

        k_val, d_val, j_val = k.iloc[-1], d.iloc[-1], j.iloc[-1]

        if pd.isna(k_val) or pd.isna(d_val):
            return {"K": None, "D": None, "J": None, "signal": "数据不足"}

        # 信号判断
        if j_val > 100:
            signal = "超买"
        elif j_val < 0:
            signal = "超卖"
        elif k_val > d_val and k_val < 80:
            signal = "多头"
        elif k_val < d_val and k_val > 20:
            signal = "空头"
        else:
            signal = "中性"

        return {
            "K": round(float(k_val), 2),
            "D": round(float(d_val), 2),
            "J": round(float(j_val), 2),
            "signal": signal,
        }

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> Dict[str, Optional[float]]:
        """计算 ATR 真实波幅"""
        if len(df) < period + 1:
            return {"ATR": None, "ATR_percent": None}

        prev_close = df["close"].shift(1)
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = tr.rolling(window=period).mean()
        atr_val = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        if pd.isna(atr_val) or current_price <= 0:
            return {"ATR": None, "ATR_percent": None}

        return {
            "ATR": round(float(atr_val), 4),
            "ATR_percent": round(float(atr_val / current_price * 100), 2),
        }

    @staticmethod
    def calculate_volume(df: pd.DataFrame, periods: Optional[List[int]] = None) -> Dict[str, Any]:
        """计算成交量均线和量比"""
        if periods is None:
            periods = [5, 10]

        if "volume" not in df.columns or df["volume"].sum() == 0:
            return {"VMA5": None, "VMA10": None, "volume_ratio": None, "volume_signal": "无成交量数据"}

        result = {}
        for period in periods:
            if len(df) >= period:
                vma = df["volume"].rolling(window=period).mean().iloc[-1]
                result[f"VMA{period}"] = round(float(vma), 0)
            else:
                result[f"VMA{period}"] = None

        # 量比 = 当日成交量 / 过去5日平均成交量
        current_vol = df["volume"].iloc[-1]
        vma5 = result.get("VMA5")
        volume_ratio = round(current_vol / vma5, 2) if vma5 and vma5 > 0 else None

        # 量能信号
        if volume_ratio is None:
            vol_signal = "数据不足"
        elif volume_ratio >= 2.0:
            vol_signal = "显著放量"
        elif volume_ratio >= 1.5:
            vol_signal = "放量"
        elif volume_ratio <= 0.5:
            vol_signal = "显著缩量"
        elif volume_ratio <= 0.8:
            vol_signal = "缩量"
        else:
            vol_signal = "正常"

        result["volume_ratio"] = volume_ratio
        result["volume_signal"] = vol_signal
        return result

    @staticmethod
    def calculate_sar(df: pd.DataFrame, acceleration: float = 0.02, maximum: float = 0.2) -> Dict[str, Any]:
        """计算 SAR 抛物线转向指标"""
        if len(df) < 2:
            return {"SAR": None, "signal": "数据不足"}

        sar = []
        ep = df["high"].iloc[0]
        af = acceleration
        trend = 1  # 1: 上升趋势, -1: 下降趋势

        # 初始化 SAR
        sar.append(df["low"].iloc[0])

        for i in range(1, len(df)):
            current_sar = sar[-1] + af * (ep - sar[-1])

            if trend == 1:
                current_sar = min(current_sar, df["low"].iloc[i-1], df["low"].iloc[i])
                if df["high"].iloc[i] > ep:
                    ep = df["high"].iloc[i]
                    af = min(af + acceleration, maximum)
                if df["low"].iloc[i] < current_sar:
                    trend = -1
                    current_sar = ep
                    ep = df["low"].iloc[i]
                    af = acceleration
            else:
                current_sar = max(current_sar, df["high"].iloc[i-1], df["high"].iloc[i])
                if df["low"].iloc[i] < ep:
                    ep = df["low"].iloc[i]
                    af = min(af + acceleration, maximum)
                if df["high"].iloc[i] > current_sar:
                    trend = 1
                    current_sar = ep
                    ep = df["high"].iloc[i]
                    af = acceleration

            sar.append(current_sar)

        current_price = df["close"].iloc[-1]
        sar_value = sar[-1]
        signal = "买入" if current_price > sar_value else "卖出"

        return {
            "SAR": round(float(sar_value), 4),
            "signal": signal,
            "trend": "上升" if trend == 1 else "下降"
        }

    @staticmethod
    def calculate_cci(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        """计算 CCI 顺势指标"""
        if len(df) < period:
            return {"CCI": None, "signal": "数据不足"}

        # 计算典型价格
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        # 计算移动平均
        sma = typical_price.rolling(window=period).mean()
        # 计算平均绝对偏差
        mad = abs(typical_price - sma).rolling(window=period).mean()
        # 计算 CCI
        cci = (typical_price - sma) / (0.015 * mad)

        cci_value = cci.iloc[-1]
        if pd.isna(cci_value):
            return {"CCI": None, "signal": "数据不足"}

        # 信号判断
        if cci_value > 100:
            signal = "超买"
        elif cci_value < -100:
            signal = "超卖"
        else:
            signal = "中性"

        return {
            "CCI": round(float(cci_value), 2),
            "signal": signal
        }

    @staticmethod
    def calculate_roc(df: pd.DataFrame, period: int = 12) -> Dict[str, Any]:
        """计算 ROC 变动率指标"""
        if len(df) < period + 1:
            return {"ROC": None, "signal": "数据不足"}

        roc = ((df["close"] / df["close"].shift(period)) - 1) * 100
        roc_value = roc.iloc[-1]

        if pd.isna(roc_value):
            return {"ROC": None, "signal": "数据不足"}

        # 信号判断
        if roc_value > 0:
            signal = "上涨"
        elif roc_value < 0:
            signal = "下跌"
        else:
            signal = "持平"

        return {
            "ROC": round(float(roc_value), 2),
            "signal": signal
        }

    @staticmethod
    def calculate_wr(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        """计算 WR 威廉指标"""
        if len(df) < period:
            return {"WR": None, "signal": "数据不足"}

        high_max = df["high"].rolling(window=period).max()
        low_min = df["low"].rolling(window=period).min()
        wr = ((high_max - df["close"]) / (high_max - low_min)) * 100

        wr_value = wr.iloc[-1]
        if pd.isna(wr_value):
            return {"WR": None, "signal": "数据不足"}

        # 信号判断
        if wr_value < -80:
            signal = "超买"
        elif wr_value > -20:
            signal = "超卖"
        else:
            signal = "中性"

        return {
            "WR": round(float(wr_value), 2),
            "signal": signal
        }
