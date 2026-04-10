"""SupportResistanceFinder.find_levels() 测试"""

from stock_analysis.support import SupportResistanceFinder


class TestFindLevels:
    """find_levels 方法测试"""

    def test_find_levels_normal(self, sample_df):
        """sample_df 返回 support/resistance/gaps 三个键"""
        result = SupportResistanceFinder.find_levels(sample_df)
        assert "support" in result
        assert "resistance" in result
        assert "gaps" in result

    def test_find_levels_short_data(self, short_df):
        """short_df(10天)数据不足时 support 和 resistance 为空列表"""
        result = SupportResistanceFinder.find_levels(short_df)
        assert result["support"] == []
        assert result["resistance"] == []

    def test_find_levels_fund_skip(self, fund_df):
        """fund_df(open=high=low=close)时跳过支撑压力位计算，返回空列表"""
        result = SupportResistanceFinder.find_levels(fund_df, asset_type="fund")
        assert result["support"] == []
        assert result["resistance"] == []

    def test_find_levels_max_count(self, sample_df):
        """support 和 resistance 最多各5个"""
        result = SupportResistanceFinder.find_levels(sample_df)
        assert len(result["support"]) <= 5
        assert len(result["resistance"]) <= 5
