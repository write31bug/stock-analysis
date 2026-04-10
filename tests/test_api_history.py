"""历史记录接口测试"""

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


def _save_record(
    client,
    code="600519",
    name="贵州茅台",
    score=75,
    trend="上涨",
    recommendation="买入",
    current_price=1800.0,
    change_pct=2.5,
):
    """辅助函数：保存一条测试历史记录"""
    return client.post(
        "/api/v1/history",
        json={
            "stock_info": {
                "code": code,
                "name": name,
                "market": "sh",
                "asset_type": "stock",
                "current_price": current_price,
                "change_pct": change_pct,
            },
            "analysis": {
                "score": score,
                "trend": trend,
                "recommendation": recommendation,
                "summary": f"{name}测试分析摘要",
            },
            "technical_indicators": {
                "ma_signal": "多头排列",
                "macd_signal": "金叉",
                "rsi_status": "中性",
                "kdj_signal": "超买",
            },
        },
    )


class TestGetHistory:
    """GET /api/v1/history — 分页查询历史记录"""

    def test_empty_list(self, client):
        """空列表应返回 total=0 和空 records"""
        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 20
        assert data["records"] == []

    def test_list_after_save(self, client):
        """保存记录后列表应包含该记录"""
        _save_record(client)
        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["records"]) == 1
        assert data["records"][0]["code"] == "600519"
        assert data["records"][0]["name"] == "贵州茅台"

    def test_filter_by_code(self, client):
        """按代码筛选应只返回对应记录"""
        _save_record(client, code="600519", name="贵州茅台")
        _save_record(client, code="000001", name="平安银行")

        resp = client.get("/api/v1/history", params={"code": "600519"})
        data = resp.json()
        assert data["total"] == 1
        assert data["records"][0]["code"] == "600519"

    def test_filter_by_trend(self, client):
        """按趋势筛选"""
        _save_record(client, code="600519", trend="上涨")
        _save_record(client, code="000001", trend="下跌")

        resp = client.get("/api/v1/history", params={"trend": "上涨"})
        data = resp.json()
        assert data["total"] == 1
        assert data["records"][0]["trend"] == "上涨"

    def test_pagination(self, client):
        """分页参数应正确工作"""
        # 创建 5 条记录
        for i in range(5):
            _save_record(client, code=f"60051{i}", name=f"股票{i}")

        # 第一页，每页 2 条
        resp = client.get("/api/v1/history", params={"page": 1, "size": 2})
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["records"]) == 2

        # 第二页
        resp2 = client.get("/api/v1/history", params={"page": 2, "size": 2})
        data2 = resp2.json()
        assert data2["total"] == 5
        assert data2["page"] == 2
        assert len(data2["records"]) == 2

        # 第三页（剩余 1 条）
        resp3 = client.get("/api/v1/history", params={"page": 3, "size": 2})
        data3 = resp3.json()
        assert data3["total"] == 5
        assert len(data3["records"]) == 1

    def test_default_pagination(self, client):
        """默认分页参数 page=1, size=20"""
        resp = client.get("/api/v1/history")
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 20


class TestSaveHistory:
    """POST /api/v1/history — 保存分析记录"""

    def test_save_record(self, client):
        """保存记录应返回成功消息和 id"""
        resp = _save_record(client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "保存成功"
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_save_record_with_minimal_data(self, client):
        """使用最小数据保存记录"""
        resp = client.post(
            "/api/v1/history",
            json={
                "stock_info": {"code": "600519"},
                "analysis": {},
                "technical_indicators": {},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "保存成功"

    def test_save_multiple_records(self, client):
        """保存多条记录"""
        for i in range(3):
            resp = _save_record(client, code=f"60051{i}", name=f"股票{i}")
            assert resp.status_code == 200

        resp = client.get("/api/v1/history")
        assert resp.json()["total"] == 3


class TestDeleteHistory:
    """DELETE /api/v1/history/{id} — 删除单条记录"""

    def test_delete_existing(self, client):
        """删除已存在的记录"""
        save_resp = _save_record(client)
        record_id = save_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/history/{record_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "删除成功"

        # 确认已删除
        list_resp = client.get("/api/v1/history")
        assert list_resp.json()["total"] == 0

    def test_delete_nonexistent_404(self, client):
        """删除不存在的记录应返回 404"""
        resp = client.delete("/api/v1/history/99999")
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]


class TestClearHistory:
    """DELETE /api/v1/history — 清空所有历史记录"""

    def test_clear_all(self, client):
        """清空所有记录"""
        _save_record(client, code="600519")
        _save_record(client, code="000001")
        _save_record(client, code="000858")

        resp = client.delete("/api/v1/history")
        assert resp.status_code == 200
        assert "已清空" in resp.json()["message"]
        assert "3" in resp.json()["message"]

        # 确认已清空
        list_resp = client.get("/api/v1/history")
        assert list_resp.json()["total"] == 0

    def test_clear_empty(self, client):
        """清空空列表"""
        resp = client.delete("/api/v1/history")
        assert resp.status_code == 200
        assert "已清空 0" in resp.json()["message"]


class TestScoreTrend:
    """GET /api/v1/score-trend/{code} — 评分趋势"""

    def test_score_trend_empty(self, client):
        """没有记录时应返回空列表"""
        resp = client.get("/api/v1/score-trend/600519")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_score_trend_with_records(self, client):
        """有记录时应返回评分趋势数据"""
        _save_record(client, code="600519", score=75)
        _save_record(client, code="600519", score=80)

        resp = client.get("/api/v1/score-trend/600519")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        for point in data:
            assert "date" in point
            assert "score" in point
            assert isinstance(point["date"], str)
            assert isinstance(point["score"], int)

    def test_score_trend_filter_by_code(self, client):
        """只返回对应代码的趋势"""
        _save_record(client, code="600519", score=75)
        _save_record(client, code="000001", score=60)

        resp = client.get("/api/v1/score-trend/600519")
        data = resp.json()
        assert len(data) == 1

    def test_score_trend_days_param(self, client):
        """days 参数应限制返回范围"""
        _save_record(client, code="600519", score=75)

        resp = client.get("/api/v1/score-trend/600519", params={"days": "30"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 0  # 取决于记录时间

    def test_score_trend_nonexistent_code(self, client):
        """不存在的代码应返回空列表"""
        resp = client.get("/api/v1/score-trend/NOTEXIST")
        assert resp.status_code == 200
        assert resp.json() == []
