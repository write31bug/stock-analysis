"""价格预警接口测试"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """创建测试客户端，触发 lifespan 事件以初始化数据库"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_alerts(client):
    """每个测试前后清理预警数据，保证测试独立性"""
    # 测试前清理
    resp = client.get("/api/v1/alerts")
    for alert in resp.json():
        client.delete(f"/api/v1/alerts/{alert['id']}")
    yield
    # 测试后清理
    resp = client.get("/api/v1/alerts")
    for alert in resp.json():
        client.delete(f"/api/v1/alerts/{alert['id']}")


class TestListAlerts:
    """GET /api/v1/alerts — 获取预警列表"""

    def test_empty_list(self, client):
        """空列表应返回空数组"""
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client):
        """创建预警后列表应包含该预警"""
        client.post(
            "/api/v1/alerts",
            json={
                "code": "600519",
                "name": "贵州茅台",
                "condition_type": "above",
                "target_value": 1800.0,
            },
        )
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["code"] == "600519"
        assert data[0]["condition_type"] == "above"
        assert data[0]["target_value"] == 1800.0

    def test_list_order_by_created_at_desc(self, client):
        """列表应按创建时间倒序排列"""
        client.post(
            "/api/v1/alerts",
            json={"code": "000001", "name": "平安银行", "condition_type": "below", "target_value": 10.0},
        )
        client.post(
            "/api/v1/alerts",
            json={"code": "000858", "name": "五粮液", "condition_type": "above", "target_value": 200.0},
        )
        resp = client.get("/api/v1/alerts")
        data = resp.json()
        assert len(data) == 2
        # 后创建的排在前面
        assert data[0]["code"] == "000858"
        assert data[1]["code"] == "000001"


class TestCreateAlert:
    """POST /api/v1/alerts — 创建预警"""

    @pytest.mark.parametrize(
        "condition_type,target_value",
        [
            ("above", 1800.0),
            ("below", 10.0),
            ("pct_change_above", 5.0),
            ("pct_change_below", -3.0),
        ],
        ids=["above", "below", "pct_change_above", "pct_change_below"],
    )
    def test_create_with_each_condition_type(self, client, condition_type, target_value):
        """测试四种条件类型均可成功创建"""
        resp = client.post(
            "/api/v1/alerts",
            json={
                "code": "600519",
                "name": "贵州茅台",
                "condition_type": condition_type,
                "target_value": target_value,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "600519"
        assert data["condition_type"] == condition_type
        assert data["target_value"] == target_value
        assert data["triggered"] is False
        assert data["id"] > 0
        assert data["created_at"] != ""

    def test_create_default_name_empty(self, client):
        """不传 name 时默认为空字符串"""
        resp = client.post(
            "/api/v1/alerts",
            json={"code": "600519", "condition_type": "above", "target_value": 1800.0},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == ""

    def test_duplicate_detection_409(self, client):
        """相同 code + condition_type + target_value 应返回 409"""
        payload = {
            "code": "600519",
            "name": "贵州茅台",
            "condition_type": "above",
            "target_value": 1800.0,
        }
        resp1 = client.post("/api/v1/alerts", json=payload)
        assert resp1.status_code == 200

        resp2 = client.post("/api/v1/alerts", json=payload)
        assert resp2.status_code == 409
        assert "已存在" in resp2.json()["detail"]

    def test_different_target_value_no_conflict(self, client):
        """相同 code 和 condition_type 但不同 target_value 应成功"""
        client.post(
            "/api/v1/alerts",
            json={"code": "600519", "condition_type": "above", "target_value": 1800.0},
        )
        resp = client.post(
            "/api/v1/alerts",
            json={"code": "600519", "condition_type": "above", "target_value": 1900.0},
        )
        assert resp.status_code == 200
        assert resp.json()["target_value"] == 1900.0


class TestDeleteAlert:
    """DELETE /api/v1/alerts/{id} — 删除预警"""

    def test_delete_existing(self, client):
        """删除已存在的预警应返回成功"""
        create_resp = client.post(
            "/api/v1/alerts",
            json={"code": "600519", "name": "贵州茅台", "condition_type": "above", "target_value": 1800.0},
        )
        alert_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/alerts/{alert_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "删除成功"

        # 确认已删除
        list_resp = client.get("/api/v1/alerts")
        assert list_resp.json() == []

    def test_delete_nonexistent_404(self, client):
        """删除不存在的预警应返回 404"""
        resp = client.delete("/api/v1/alerts/99999")
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]


class TestCheckAlerts:
    """POST /api/v1/alerts/check — 检查预警"""

    def test_check_no_alerts(self, client):
        """没有预警时应返回提示信息"""
        resp = client.post("/api/v1/alerts/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["triggered_count"] == 0
        assert "没有" in data["message"]

    def test_check_with_untriggered_alerts(self, client):
        """有待检查的预警时端点应正常工作（测试模式下不会真正触发）"""
        client.post(
            "/api/v1/alerts",
            json={"code": "600519", "name": "贵州茅台", "condition_type": "above", "target_value": 99999.0},
        )
        resp = client.post("/api/v1/alerts/check")
        assert resp.status_code == 200
        data = resp.json()
        assert "triggered_count" in data
        assert isinstance(data["triggered_count"], int)
