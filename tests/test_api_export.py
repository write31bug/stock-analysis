"""数据导出接口测试"""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """创建测试客户端，触发 lifespan 事件以初始化数据库"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_history(client):
    """每个测试前后清理历史记录，保证测试独立性"""
    # 测试前清理
    client.delete("/api/v1/history")
    yield
    # 测试后清理
    client.delete("/api/v1/history")


def _save_test_record(client, code="600519", name="贵州茅台", score=75, trend="上涨"):
    """辅助函数：保存一条测试历史记录"""
    resp = client.post(
        "/api/v1/history",
        json={
            "stock_info": {
                "code": code,
                "name": name,
                "market": "sh",
                "asset_type": "stock",
                "current_price": 1800.0,
                "change_pct": 2.5,
            },
            "analysis": {
                "score": score,
                "trend": trend,
                "recommendation": "买入",
                "summary": "测试摘要",
            },
            "technical_indicators": {
                "ma_signal": "多头排列",
                "macd_signal": "金叉",
                "rsi_status": "中性",
                "kdj_signal": "超买",
            },
        },
    )
    return resp


class TestExportHistory:
    """GET /api/v1/export/history — 导出历史记录 CSV"""

    def test_export_history_csv_content_type(self, client):
        """导出接口应返回 CSV 内容类型"""
        resp = client.get("/api/v1/export/history")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_history_csv_headers(self, client):
        """CSV 应包含正确的表头"""
        resp = client.get("/api/v1/export/history")
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)

        expected_headers = [
            "代码",
            "名称",
            "现价",
            "涨跌幅",
            "评分",
            "趋势",
            "建议",
            "MA信号",
            "MACD信号",
            "RSI状态",
            "KDJ信号",
            "分析时间",
        ]
        assert headers == expected_headers

    def test_export_history_empty(self, client):
        """没有记录时 CSV 应只有表头"""
        resp = client.get("/api/v1/export/history")
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        rows = list(reader)
        assert len(headers) > 0
        assert len(rows) == 0

    def test_export_history_with_records(self, client):
        """有记录时 CSV 应包含数据行"""
        _save_test_record(client)

        resp = client.get("/api/v1/export/history")
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        next(reader)  # skip headers
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0][0] == "600519"
        assert rows[0][1] == "贵州茅台"

    def test_export_history_filter_by_code(self, client):
        """按代码筛选导出"""
        _save_test_record(client, code="600519", name="贵州茅台")
        _save_test_record(client, code="000001", name="平安银行")

        resp = client.get("/api/v1/export/history", params={"code": "600519"})
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        next(reader)  # skip headers
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0][0] == "600519"

    def test_export_history_content_disposition(self, client):
        """响应应包含 Content-Disposition 头"""
        resp = client.get("/api/v1/export/history")
        assert "content-disposition" in resp.headers
        assert "attachment" in resp.headers["content-disposition"]
        assert "history_" in resp.headers["content-disposition"]
        assert ".csv" in resp.headers["content-disposition"]


class TestExportAnalysisCsv:
    """GET /api/v1/export/csv — 导出分析结果 CSV"""

    def test_export_csv_content_type(self, client):
        """导出接口应返回 CSV 内容类型"""
        resp = client.get("/api/v1/export/csv", params={"codes": "600519"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_csv_headers(self, client):
        """CSV 应包含正确的表头"""
        resp = client.get("/api/v1/export/csv", params={"codes": "600519"})
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)

        expected_headers = [
            "代码",
            "名称",
            "现价",
            "涨跌幅",
            "评分",
            "趋势",
            "建议",
            "MA信号",
            "MACD信号",
            "RSI状态",
            "KDJ信号",
            "分析时间",
        ]
        assert headers == expected_headers

    def test_export_csv_empty_codes(self, client):
        """空代码列表应返回纯文本提示"""
        resp = client.get("/api/v1/export/csv", params={"codes": ""})
        assert resp.status_code == 200

    def test_export_csv_content_disposition(self, client):
        """响应应包含 Content-Disposition 头"""
        resp = client.get("/api/v1/export/csv", params={"codes": "600519"})
        assert "content-disposition" in resp.headers
        assert "attachment" in resp.headers["content-disposition"]
        assert "analysis_" in resp.headers["content-disposition"]
        assert ".csv" in resp.headers["content-disposition"]

    def test_export_csv_multiple_codes(self, client):
        """多只股票代码导出"""
        resp = client.get("/api/v1/export/csv", params={"codes": "600519,000001"})
        assert resp.status_code == 200
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        next(reader)  # skip headers
        rows = list(reader)
        # 应该有两行数据（即使分析失败也会有错误行）
        assert len(rows) >= 2
