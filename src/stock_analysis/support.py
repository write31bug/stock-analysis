"""支撑位和压力位识别器"""

import logging
from typing import Dict, List

import pandas as pd

logger = logging.getLogger("stock_analysis.support")


class SupportResistanceFinder:
    """支撑位和压力位识别器"""

    @staticmethod
    def find_levels(df: pd.DataFrame, window: int = 5, asset_type: str = "stock") -> Dict[str, List]:
        """识别支撑位、压力位和缺口

        Args:
            df: 行情数据
            window: 局部极值窗口大小
            asset_type: 资产类型，基金类型跳过支撑压力位计算
        """
        support_levels: List[float] = []
        resistance_levels: List[float] = []
        gaps: List[Dict] = []

        if len(df) < window * 2:
            return {"support": support_levels, "resistance": resistance_levels, "gaps": gaps}

        # 开放式基金 open=high=low=close，支撑压力位无意义
        if asset_type == "fund" and "open" in df.columns and (df["high"] == df["low"]).all():
            return {"support": support_levels, "resistance": resistance_levels, "gaps": gaps}

        # 局部极值识别（排除当前位置自身）
        for i in range(window, len(df) - window):
            high = df["high"].iloc[i]
            low = df["low"].iloc[i]
            # 排除位置 i，只与窗口内其他位置比较
            window_highs = df["high"].iloc[i - window : i].tolist() + df["high"].iloc[i + 1 : i + window + 1].tolist()
            window_lows = df["low"].iloc[i - window : i].tolist() + df["low"].iloc[i + 1 : i + window + 1].tolist()

            # 局部高点（压力位）：严格大于窗口内所有其他值
            if all(high >= wh for wh in window_highs):
                resistance_levels.append(round(float(high), 4))

            # 局部低点（支撑位）：严格小于窗口内所有其他值
            if all(low <= wl for wl in window_lows):
                support_levels.append(round(float(low), 4))

        # 缺口检测
        for i in range(1, len(df)):
            prev_high = df["high"].iloc[i - 1]
            prev_low = df["low"].iloc[i - 1]
            curr_high = df["high"].iloc[i]
            curr_low = df["low"].iloc[i]

            if curr_low > prev_high:
                # 向上跳空
                gaps.append(
                    {
                        "type": "向上跳空",
                        "gap_start": round(float(prev_high), 4),
                        "gap_end": round(float(curr_low), 4),
                        "size": round((curr_low - prev_high) / prev_high * 100, 2) if prev_high > 0 else 0,
                    }
                )
            elif curr_high < prev_low:
                # 向下跳空
                gaps.append(
                    {
                        "type": "向下跳空",
                        "gap_start": round(float(curr_high), 4),
                        "gap_end": round(float(prev_low), 4),
                        "size": round((prev_low - curr_high) / curr_high * 100, 2) if curr_high > 0 else 0,
                    }
                )

        # 取最近5个支撑/压力位
        support_levels = sorted(support_levels, reverse=True)[:5]
        resistance_levels = sorted(resistance_levels)[:5]

        return {
            "support": support_levels,
            "resistance": resistance_levels,
            "gaps": gaps[-3:] if len(gaps) > 3 else gaps,
        }
