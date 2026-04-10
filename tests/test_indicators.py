"""TechnicalIndicators 类的单元测试"""

from stock_analysis.indicators import TechnicalIndicators


class TestCalculateMA:
    """移动平均线 MA 测试"""

    def test_calculate_ma_normal(self, sample_df):
        """60天数据：MA5/10/20/60 都不为 None"""
        result = TechnicalIndicators.calculate_ma(sample_df)
        assert result["MA5"] is not None
        assert result["MA10"] is not None
        assert result["MA20"] is not None
        assert result["MA60"] is not None

    def test_calculate_ma_short_data(self, short_df):
        """10天数据：MA60 应为 None"""
        result = TechnicalIndicators.calculate_ma(short_df)
        assert result["MA60"] is None


class TestCalculateMACD:
    """MACD 指标测试"""

    def test_calculate_macd_normal(self, sample_df):
        """60天数据：返回 DIF/DEA/MACD/signal/divergence 键"""
        result = TechnicalIndicators.calculate_macd(sample_df)
        assert "DIF" in result
        assert "DEA" in result
        assert "MACD" in result
        assert "signal" in result
        assert "divergence" in result

    def test_calculate_macd_short_data(self, short_df):
        """10天数据（<26）：signal 应为 '数据不足'"""
        result = TechnicalIndicators.calculate_macd(short_df)
        assert result["signal"] == "数据不足"


class TestCalculateRSI:
    """RSI 相对强弱指数测试"""

    def test_calculate_rsi_normal(self, sample_df):
        """60天数据：RSI6/12/24 都在 0-100 范围内"""
        result = TechnicalIndicators.calculate_rsi(sample_df)
        assert 0 <= result["RSI6"] <= 100
        assert 0 <= result["RSI12"] <= 100
        assert 0 <= result["RSI24"] <= 100


class TestCalculateBollinger:
    """布林带 BOLL 测试"""

    def test_calculate_bollinger_normal(self, sample_df):
        """60天数据：upper > middle > lower"""
        result = TechnicalIndicators.calculate_bollinger(sample_df)
        assert result["upper"] > result["middle"] > result["lower"]

    def test_calculate_bollinger_short_data(self, short_df):
        """10天数据（<20）：position 应为 '数据不足'"""
        result = TechnicalIndicators.calculate_bollinger(short_df)
        assert result["position"] == "数据不足"


class TestCalculateKDJ:
    """KDJ 随机指标测试"""

    def test_calculate_kdj_normal(self, sample_df):
        """60天数据：K/D/J 存在，signal 为字符串"""
        result = TechnicalIndicators.calculate_kdj(sample_df)
        assert result["K"] is not None
        assert result["D"] is not None
        assert result["J"] is not None
        assert isinstance(result["signal"], str)

    def test_calculate_kdj_short_data(self, short_df):
        """10天数据（>=9）：应正常返回，signal 不为 '数据不足'"""
        result = TechnicalIndicators.calculate_kdj(short_df)
        assert result["signal"] != "数据不足"


class TestCalculateATR:
    """ATR 真实波幅测试"""

    def test_calculate_atr_normal(self, sample_df):
        """60天数据：ATR > 0, ATR_percent > 0"""
        result = TechnicalIndicators.calculate_atr(sample_df)
        assert result["ATR"] is not None
        assert result["ATR"] > 0
        assert result["ATR_percent"] is not None
        assert result["ATR_percent"] > 0

    def test_calculate_atr_short_data(self, short_df):
        """10天数据（<15）：ATR 应为 None"""
        result = TechnicalIndicators.calculate_atr(short_df)
        assert result["ATR"] is None


class TestCalculateVolume:
    """成交量指标测试"""

    def test_calculate_volume_normal(self, sample_df):
        """60天数据：volume_ratio 和 volume_signal 存在"""
        result = TechnicalIndicators.calculate_volume(sample_df)
        assert "volume_ratio" in result
        assert "volume_signal" in result

    def test_calculate_volume_zero(self, zero_volume_df):
        """全零成交量：volume_signal 应为 '无成交量数据'"""
        result = TechnicalIndicators.calculate_volume(zero_volume_df)
        assert result["volume_signal"] == "无成交量数据"
