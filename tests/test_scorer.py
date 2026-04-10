"""Scorer.calculate_score() 方法的单元测试"""

import numpy as np

from stock_analysis.indicators import TechnicalIndicators
from stock_analysis.scorer import Scorer


def _build_indicator_dicts(df):
    """辅助函数：用 TechnicalIndicators 计算所有指标并返回字典元组"""
    ma = TechnicalIndicators.calculate_ma(df)
    macd = TechnicalIndicators.calculate_macd(df)
    rsi = TechnicalIndicators.calculate_rsi(df)
    bollinger = TechnicalIndicators.calculate_bollinger(df)
    kdj = TechnicalIndicators.calculate_kdj(df)
    volume = TechnicalIndicators.calculate_volume(df)
    return ma, macd, rsi, bollinger, kdj, volume


class TestScorerCalculate:
    """Scorer.calculate_score() 测试"""

    def test_score_range(self, sample_df):
        """评分结果应在 0-100 范围内"""
        ma, macd, rsi, bollinger, kdj, volume = _build_indicator_dicts(sample_df)
        score, trend, recommendation = Scorer.calculate_score(sample_df, ma, macd, rsi, bollinger, kdj, volume)
        assert 0 <= score <= 100

    def test_trend_types(self, sample_df):
        """趋势应为5种之一"""
        valid_trends = {"强势上涨", "上涨趋势", "震荡整理", "下跌趋势", "强势下跌"}
        ma, macd, rsi, bollinger, kdj, volume = _build_indicator_dicts(sample_df)
        score, trend, recommendation = Scorer.calculate_score(sample_df, ma, macd, rsi, bollinger, kdj, volume)
        assert trend in valid_trends

    def test_nan_price(self, sample_df):
        """close 列含 NaN 时，评分应为 50"""
        df = sample_df.copy()
        df.loc[df.index[-1], "close"] = np.nan
        ma, macd, rsi, bollinger, kdj, volume = _build_indicator_dicts(df)
        score, trend, recommendation = Scorer.calculate_score(df, ma, macd, rsi, bollinger, kdj, volume)
        assert score == 50

    def test_volume_bonus(self, sample_df):
        """volume_ratio >= 2.0 时，相比正常量能应获得更高评分"""
        ma, macd, rsi, bollinger, kdj, _ = _build_indicator_dicts(sample_df)

        # 基准评分（正常量能）
        normal_volume = {"volume_ratio": 1.0, "volume_signal": "正常"}
        base_score, _, _ = Scorer.calculate_score(sample_df, ma, macd, rsi, bollinger, kdj, normal_volume)

        # 放量评分（volume_ratio >= 2.0）
        surge_volume = {"volume_ratio": 2.5, "volume_signal": "显著放量"}
        surge_score, _, _ = Scorer.calculate_score(sample_df, ma, macd, rsi, bollinger, kdj, surge_volume)

        assert surge_score > base_score
