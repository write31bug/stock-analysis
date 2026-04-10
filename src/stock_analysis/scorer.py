"""综合评分器"""

import logging
from typing import Dict, Optional, Tuple

import pandas as pd

from .constants import (
    BB_LOWER_THRESHOLD,
    BB_UPPER_THRESHOLD,
    SCORE_DOWN,
    SCORE_SIDEWAYS_LOW,
    SCORE_STRONG_UP,
    SCORE_UP,
)

logger = logging.getLogger("stock_analysis.scorer")


class Scorer:
    """综合评分器"""

    @staticmethod
    def calculate_score(
        df: pd.DataFrame,
        ma: Dict,
        macd: Dict,
        rsi: Dict,
        bollinger: Dict,
        kdj: Optional[Dict] = None,
        volume: Optional[Dict] = None,
    ) -> Tuple[int, str, str]:
        """
        计算综合评分。

        评分维度：
          - 基础分 50
          - 均线趋势 ±20（排列 + 价格位置 ±8）
          - MACD ±15（金叉/死叉 + 柱状方向）
          - RSI ±15（超买超卖）
          - 布林带 ±10（突破/接近轨道）

        Returns:
            (评分, 趋势, 建议)
        """
        score = 50
        current_price = df["close"].iloc[-1]

        # NaN 安全检查
        if pd.isna(current_price):
            return 50, "数据不足", "当前价格数据缺失，无法准确评分"

        # 1. 均线趋势 (±20) — 分层处理，MA60 缺失时仍评短期趋势
        if ma.get("MA5") and ma.get("MA10") and ma.get("MA20"):
            # 短期均线排列 (±12)
            if ma["MA5"] > ma["MA10"] > ma["MA20"]:
                score += 12  # 短期多头
            elif ma["MA5"] < ma["MA10"] < ma["MA20"]:
                score -= 12  # 短期空头

            # 长期均线确认 (±8)
            if ma.get("MA60") is not None:
                if ma["MA5"] > ma["MA10"] > ma["MA20"] > ma["MA60"]:
                    score += 8  # 完美多头（在短期多头基础上追加）
                elif ma["MA5"] < ma["MA10"] < ma["MA20"] < ma["MA60"]:
                    score -= 8  # 完美空头（在短期空头基础上追加）

            # 价格与均线关系 (±8)
            if current_price > ma["MA5"]:
                score += 5
            else:
                score -= 5
            if current_price > ma["MA20"]:
                score += 3
            else:
                score -= 3

        # 2. MACD (±15)
        if macd.get("signal") == "金叉":
            score += 10
        elif macd.get("signal") == "死叉":
            score -= 10

        if macd.get("MACD") is not None:
            score += 5 if macd["MACD"] > 0 else -5

        # 3. RSI (±15)
        rsi_val = rsi.get("RSI12")
        if rsi_val is not None:
            if rsi_val < 20:
                score += 15  # 严重超卖
            elif rsi_val < 30:
                score += 10  # 超卖
            elif rsi_val > 80:
                score -= 15  # 严重超买
            elif rsi_val > 70:
                score -= 10  # 超买

        # 4. 布林带 (±10)
        bb_pos = bollinger.get("bb_position")
        if bb_pos is not None:
            if bollinger["position"] == "突破下轨":
                score += 10
            elif bollinger["position"] == "突破上轨":
                score -= 10
            elif bb_pos < BB_LOWER_THRESHOLD:
                score += 5  # 接近下轨
            elif bb_pos > BB_UPPER_THRESHOLD:
                score -= 5  # 接近上轨
            # 中位 (0.3~0.7) 不加减分

        # 5. KDJ (±10)
        if kdj and kdj.get("K") is not None:
            if kdj["signal"] == "超卖":
                score += 8
            elif kdj["signal"] == "超买":
                score -= 8
            elif kdj["signal"] == "多头":
                score += 4
            elif kdj["signal"] == "空头":
                score -= 4

        # 6. 成交量/量能 (±8)
        if volume and volume.get("volume_ratio") is not None:
            vr = volume["volume_ratio"]
            if vr >= 2.0:
                score += 5  # 显著放量（关注突破）
            elif vr >= 1.5:
                score += 3  # 放量
            elif vr <= 0.5:
                score -= 3  # 显著缩量
            elif vr <= 0.8:
                score -= 1  # 缩量

        final_score = max(0, min(100, score))

        # 趋势判断
        if final_score >= SCORE_STRONG_UP:
            trend = "强势上涨"
            recommendation = "技术面强势，多指标共振偏多"
        elif final_score >= SCORE_UP:
            trend = "上涨趋势"
            recommendation = "技术面偏多，短期趋势向上"
        elif final_score >= SCORE_SIDEWAYS_LOW:
            trend = "震荡整理"
            recommendation = "技术面中性，方向不明确"
        elif final_score >= SCORE_DOWN:
            trend = "下跌趋势"
            recommendation = "技术面偏空，短期趋势向下"
        else:
            trend = "强势下跌"
            recommendation = "技术面弱势，多指标共振偏空"

        return final_score, trend, recommendation
