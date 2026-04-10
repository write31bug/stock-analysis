"""分析接口测试"""

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

# 期望的 19 个技术指标序列
EXPECTED_INDICATOR_SERIES = [
    "MA5", "MA10", "MA20", "MA60",
    "DIF", "DEA", "MACD",
    "RSI6", "RSI12", "RSI24",
    "K", "D", "J",
    "BOLL_UPPER", "BOLL_MIDDLE", "BOLL_LOWER",
    "OBV", "CCI", "WR",
]

OHLCV_FIELDS = ["date", "open", "high", "low", "close", "volume"]

# 模块级缓存，避免重复 API 调用
_analyze_cache = {}


@pytest.fixture
def client():
    """创建测试客户端，触发 lifespan 事件以初始化数据库"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def analyze_600519(client):
    """共享的 600519 分析响应（整个测试只调一次 API）"""
    if "600519" not in _analyze_cache:
        resp = client.get("/api/v1/analyze/600519", params={"test": "true"})
        assert resp.status_code == 200
        _analyze_cache["600519"] = resp.json()
    return _analyze_cache["600519"]


class TestAnalyzeStock:
    """GET /api/v1/analyze/{code} — 单股技术分析"""

    def test_analyze_with_test_mode(self, analyze_600519):
        data = analyze_600519
        assert "stock_info" in data
        assert "analysis" in data
        assert "technical_indicators" in data
        assert "key_levels" in data
        assert "ohlcv" in data
        assert "indicator_series" in data

    def test_stock_info_structure(self, analyze_600519):
        si = analyze_600519["stock_info"]
        assert si["code"] == "600519"
        assert "name" in si
        assert "current_price" in si
        assert "change_pct" in si
        assert "market" in si
        assert "asset_type" in si
        assert "update_time" in si
        assert si["is_mock_data"] is True

    def test_analysis_structure(self, analyze_600519):
        analysis = analyze_600519["analysis"]
        assert "score" in analysis
        assert "trend" in analysis
        assert "recommendation" in analysis
        assert "summary" in analysis
        assert isinstance(analysis["score"], int)
        assert isinstance(analysis["trend"], str)
        assert isinstance(analysis["recommendation"], str)

    def test_all_19_indicator_series_exist(self, analyze_600519):
        series = analyze_600519["indicator_series"]
        for name in EXPECTED_INDICATOR_SERIES:
            assert name in series, f"缺少指标序列: {name}"

    def test_indicator_series_data_points(self, analyze_600519):
        series = analyze_600519["indicator_series"]
        for name in EXPECTED_INDICATOR_SERIES:
            points = series[name]
            assert isinstance(points, list)
            assert len(points) > 0, f"指标 {name} 数据点为空"
            for point in points:
                assert "date" in point
                assert "value" in point

    def test_ohlcv_structure(self, analyze_600519):
        ohlcv = analyze_600519["ohlcv"]
        assert isinstance(ohlcv, list)
        assert len(ohlcv) > 0
        for item in ohlcv:
            for field in OHLCV_FIELDS:
                assert field in item
            assert item["high"] >= item["low"]
            assert item["volume"] >= 0

    def test_ohlcv_date_format(self, analyze_600519):
        for item in analyze_600519["ohlcv"]:
            d = item["date"]
            assert len(d) == 10 and d[4] == "-" and d[7] == "-"

    def test_days_param_default_60(self, analyze_600519):
        assert len(analyze_600519["ohlcv"]) == 60

    def test_technical_indicators_structure(self, analyze_600519):
        ti = analyze_600519["technical_indicators"]
        for key in ("ma", "macd", "rsi", "bollinger", "kdj"):
            assert key in ti

    def test_key_levels_structure(self, analyze_600519):
        assert isinstance(analyze_600519["key_levels"], dict)

    def test_days_param(self, client):
        resp = client.get("/api/v1/analyze/600519", params={"test": "true", "days": "30"})
        assert len(resp.json()["ohlcv"]) == 30

    def test_different_codes(self, client):
        r1 = client.get("/api/v1/analyze/600519", params={"test": "true"})
        r2 = client.get("/api/v1/analyze/000001", params={"test": "true"})
        assert r1.json()["stock_info"]["code"] == "600519"
        assert r2.json()["stock_info"]["code"] == "000001"
        assert r1.json()["stock_info"]["current_price"] != r2.json()["stock_info"]["current_price"]


class TestBatchAnalyze:
    """POST /api/v1/batch + GET /api/v1/batch/{task_id} — 批量分析（全部用 test=true 避免）"""

    def test_submit_batch(self, client):
        """提交批量分析任务应返回 task_id"""
        resp = client.post("/api/v1/batch", json={
            "codes": ["600519"], "days": 60, "test": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "running"
        assert data["total"] == 1
        # 等后台完成，避免影响后续测试
        for _ in range(10):
            r = client.get(f"/api/v1/batch/{data['task_id']}")
            if r.json()["status"] == "completed":
                break
            time.sleep(0.1)

    def test_get_batch_status_404(self, client):
        resp = client.get("/api/v1/batch/notexist")
        assert resp.status_code == 404

    def test_batch_completes(self, client):
        """提交 test=true 批量任务并等待完成"""
        resp = client.post("/api/v1/batch", json={
            "codes": ["600519"], "days": 30, "test": True,
        })
        task_id = resp.json()["task_id"]

        for _ in range(20):
            r = client.get(f"/api/v1/batch/{task_id}")
            data = r.json()
            if data["status"] == "completed":
                break
            time.sleep(0.1)
        else:
            pytest.fail("批量任务未完成")

        assert data["status"] == "completed"
        assert data["progress"] == 1
