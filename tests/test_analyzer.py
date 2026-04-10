"""StockAnalyzer 离线分析功能测试"""

import pytest

from stock_analysis.analyzer import StockAnalyzer


@pytest.fixture
def analyzer():
    return StockAnalyzer()


class TestAnalyzeWithMockData:
    """analyze_with_mock_data 方法测试"""

    def test_analyze_with_mock_data(self, analyzer):
        """返回包含 stock_info/technical_indicators/key_levels/analysis 四个顶层键"""
        result = analyzer.analyze_with_mock_data("600519")
        assert "stock_info" in result
        assert "technical_indicators" in result
        assert "key_levels" in result
        assert "analysis" in result

    def test_analyze_with_mock_data_structure(self, analyzer):
        """stock_info 包含 code/name/market/asset_type/current_price/change_pct"""
        result = analyzer.analyze_with_mock_data("600519")
        info = result["stock_info"]
        assert "code" in info
        assert "name" in info
        assert "market" in info
        assert "asset_type" in info
        assert "current_price" in info
        assert "change_pct" in info

    def test_analyze_with_mock_data_indicators(self, analyzer):
        """technical_indicators 包含 ma/macd/rsi/bollinger/kdj/atr/volume_analysis"""
        result = analyzer.analyze_with_mock_data("600519")
        ti = result["technical_indicators"]
        assert "ma" in ti
        assert "macd" in ti
        assert "rsi" in ti
        assert "bollinger" in ti
        assert "kdj" in ti
        assert "atr" in ti
        assert "volume_analysis" in ti

    def test_analyze_with_mock_data_score(self, analyzer):
        """analysis 包含 score(int)/trend(str)/recommendation(str)/summary(str)"""
        result = analyzer.analyze_with_mock_data("600519")
        analysis = result["analysis"]
        assert isinstance(analysis["score"], int)
        assert isinstance(analysis["trend"], str)
        assert isinstance(analysis["recommendation"], str)
        assert isinstance(analysis["summary"], str)


class TestAnalyzeBatch:
    """analyze_batch 方法测试"""

    def test_analyze_batch(self, analyzer):
        """analyze_batch 返回 results/summary/timestamp"""
        result = analyzer.analyze_batch(["600519", "000001"], test=True)
        assert "results" in result
        assert "summary" in result
        assert "timestamp" in result

    def test_analyze_batch_summary(self, analyzer):
        """summary 包含 total/valid/failed_count/avg_score"""
        result = analyzer.analyze_batch(["600519", "000001"], test=True)
        summary = result["summary"]
        assert "total" in summary
        assert "valid" in summary
        assert "failed_count" in summary
        assert "avg_score" in summary


class TestGenerateSummary:
    """_generate_summary 方法测试"""

    def test_generate_summary(self, analyzer):
        """_generate_summary 返回非空字符串"""
        result = analyzer.analyze_with_mock_data("600519")
        summary = result["analysis"]["summary"]
        assert isinstance(summary, str)
        assert len(summary) > 0
