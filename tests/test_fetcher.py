"""StockDataFetcher 单元测试 - 纯逻辑方法"""

from unittest.mock import patch

from stock_analysis.fetcher import StockDataFetcher


class TestNormalizeStockCode:
    """normalize_stock_code 代码标准化测试"""

    def test_normalize_stock_code_ashare_sh(self):
        """上海交易所代码（6开头）"""
        code, market, asset_type = StockDataFetcher.normalize_stock_code("600519")
        assert code == "600519"
        assert market == "ashare"
        assert asset_type == "stock"

    def test_normalize_stock_code_ashare_sz(self):
        """深圳交易所代码（0开头，非基金前缀）"""
        code, market, asset_type = StockDataFetcher.normalize_stock_code("000001")
        assert code == "000001"
        assert market == "ashare"
        assert asset_type == "stock"

    def test_normalize_stock_code_hkstock(self):
        """港股代码（HK. 前缀）"""
        code, market, asset_type = StockDataFetcher.normalize_stock_code("HK.00700")
        assert code == "00700"
        assert market == "hkstock"
        assert asset_type == "stock"

    def test_normalize_stock_code_usstock(self):
        """美股代码（纯字母）"""
        code, market, asset_type = StockDataFetcher.normalize_stock_code("AAPL")
        assert code == "AAPL"
        assert market == "usstock"
        assert asset_type == "stock"


class TestGetFundType:
    """get_fund_type 基金类型识别测试"""

    def test_get_fund_type_etf(self):
        """ETF 类型识别（15/51/58开头）"""
        assert StockDataFetcher.get_fund_type("159934") == "etf"
        assert StockDataFetcher.get_fund_type("510300") == "etf"
        assert StockDataFetcher.get_fund_type("582000") == "etf"

    def test_get_fund_type_lof(self):
        """LOF 类型识别（16开头）"""
        assert StockDataFetcher.get_fund_type("163406") == "lof"

    def test_get_fund_type_open(self):
        """开放式基金识别（00/01/11/18开头）"""
        assert StockDataFetcher.get_fund_type("001316") == "open"
        assert StockDataFetcher.get_fund_type("012345") == "open"
        assert StockDataFetcher.get_fund_type("110011") == "open"
        assert StockDataFetcher.get_fund_type("180001") == "open"

    def test_get_fund_type_stock(self):
        """普通股票识别（6开头，不属于任何基金前缀）"""
        assert StockDataFetcher.get_fund_type("600519") == "open"


class TestBuildSinaSymbol:
    """_build_sina_symbol 新浪代码构建测试"""

    def test_build_sina_symbol(self):
        """上海交易所用 sh 前缀，深圳用 sz 前缀"""
        assert StockDataFetcher._build_sina_symbol("600519") == "sh600519"
        assert StockDataFetcher._build_sina_symbol("000001") == "sz000001"
        # 5/7/9 开头也属于上海
        assert StockDataFetcher._build_sina_symbol("500001") == "sh500001"


class TestBuildYfinanceCode:
    """_build_yfinance_code yfinance 代码构建测试"""

    def test_build_yfinance_code_hk(self):
        """港股 yfinance 代码：补零到4位 + .HK"""
        assert StockDataFetcher._build_yfinance_code("700", "hkstock") == "0700.HK"
        assert StockDataFetcher._build_yfinance_code("00700", "hkstock") == "00700.HK"

    def test_build_yfinance_code_us(self):
        """美股 yfinance 代码：原样返回"""
        assert StockDataFetcher._build_yfinance_code("AAPL", "usstock") == "AAPL"
        assert StockDataFetcher._build_yfinance_code("MSFT", "usstock") == "MSFT"


class TestFetchDataNoNetwork:
    """fetch_data 无网络时返回 None"""

    def test_fetch_data_no_network(self):
        """mock requests.get 抛异常，fetch_data 应返回 None"""
        with patch("stock_analysis.fetcher.REQUESTS_AVAILABLE", False), patch(
            "stock_analysis.fetcher.YFINANCE_AVAILABLE", False
        ), patch("stock_analysis.fetcher.AKSHARE_AVAILABLE", False):
            result = StockDataFetcher.fetch_data("600519", "ashare", "stock", days=60)
            assert result is None
