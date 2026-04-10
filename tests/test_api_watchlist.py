"""自选股接口测试"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from stock_analysis.config import load_config, save_config


@pytest.fixture
def client():
    """创建测试客户端，触发 lifespan 事件"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_watchlist(client):
    """每个测试前后清理自选股数据，保证测试独立性"""
    # 测试前清理：删除所有自选股
    resp = client.get("/api/v1/watchlist")
    for item in resp.json():
        client.delete(f"/api/v1/watchlist/{item['code']}")
    # 清理额外分组
    groups_resp = client.get("/api/v1/watchlist/groups")
    for group in groups_resp.json():
        if group != "默认":
            client.delete(f"/api/v1/watchlist/group/{group}")
    # 清理 config 中的 watchlist_groups 残留
    config = load_config()
    config["watchlist_groups"] = []
    save_config(config)
    yield
    # 测试后清理
    resp = client.get("/api/v1/watchlist")
    for item in resp.json():
        client.delete(f"/api/v1/watchlist/{item['code']}")
    groups_resp = client.get("/api/v1/watchlist/groups")
    for group in groups_resp.json():
        if group != "默认":
            client.delete(f"/api/v1/watchlist/group/{group}")
    config = load_config()
    config["watchlist_groups"] = []
    save_config(config)


class TestGetWatchlist:
    """GET /api/v1/watchlist — 获取自选股列表"""

    def test_empty_list(self, client):
        """空列表应返回空数组"""
        resp = client.get("/api/v1/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_add(self, client):
        """添加后列表应包含该股票"""
        client.post("/api/v1/watchlist", json={"code": "600519", "name": "贵州茅台", "group": "默认"})
        resp = client.get("/api/v1/watchlist")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["code"] == "600519"
        assert data[0]["name"] == "贵州茅台"
        # 600519 是沪市股票，自动分组为"股票"
        assert data[0]["group"] == "股票"

    def test_filter_by_group(self, client):
        """按分组筛选应只返回该分组的股票"""
        client.post("/api/v1/watchlist", json={"code": "600519", "name": "贵州茅台", "group": "白酒"})
        client.post("/api/v1/watchlist", json={"code": "000001", "name": "平安银行", "group": "银行"})

        resp_baijiu = client.get("/api/v1/watchlist", params={"group": "白酒"})
        assert resp_baijiu.status_code == 200
        data = resp_baijiu.json()
        assert len(data) == 1
        assert data[0]["code"] == "600519"

        resp_bank = client.get("/api/v1/watchlist", params={"group": "银行"})
        assert resp_bank.status_code == 200
        data = resp_bank.json()
        assert len(data) == 1
        assert data[0]["code"] == "000001"

        resp_all = client.get("/api/v1/watchlist")
        assert len(resp_all.json()) == 2

    def test_filter_nonexistent_group(self, client):
        """筛选不存在的分组应返回空列表"""
        client.post("/api/v1/watchlist", json={"code": "600519", "name": "贵州茅台", "group": "默认"})
        resp = client.get("/api/v1/watchlist", params={"group": "不存在的分组"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestAddToWatchlist:
    """POST /api/v1/watchlist — 添加自选股"""

    def test_add_with_group(self, client):
        """添加到指定分组"""
        resp = client.post(
            "/api/v1/watchlist",
            json={"code": "600519", "name": "贵州茅台", "group": "白酒"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "添加成功"
        items = data["watchlist"]
        assert any(i["code"] == "600519" and i["group"] == "白酒" for i in items)

    def test_add_without_group_defaults(self, client):
        """不指定分组时自动判断分组"""
        resp = client.post(
            "/api/v1/watchlist",
            json={"code": "600519", "name": "贵州茅台"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "添加成功"
        items = data["watchlist"]
        added = [i for i in items if i["code"] == "600519"]
        assert len(added) == 1
        # 600519 是沪市股票，自动分组为"股票"
        assert added[0]["group"] == "股票"

    def test_duplicate_detection(self, client):
        """重复添加相同代码应返回 '已存在'"""
        payload = {"code": "600519", "name": "贵州茅台", "group": "默认"}
        resp1 = client.post("/api/v1/watchlist", json=payload)
        assert resp1.status_code == 200
        assert resp1.json()["message"] == "添加成功"

        resp2 = client.post("/api/v1/watchlist", json=payload)
        assert resp2.status_code == 200
        assert resp2.json()["message"] == "已存在"

    def test_add_multiple_stocks(self, client):
        """添加多只股票"""
        for code, name in [("600519", "贵州茅台"), ("000001", "平安银行"), ("000858", "五粮液")]:
            resp = client.post("/api/v1/watchlist", json={"code": code, "name": name})
            assert resp.status_code == 200
            assert resp.json()["message"] == "添加成功"

        resp = client.get("/api/v1/watchlist")
        assert len(resp.json()) == 3


class TestRemoveFromWatchlist:
    """DELETE /api/v1/watchlist/{code} — 删除自选股"""

    def test_delete_existing(self, client):
        """删除已存在的自选股"""
        client.post("/api/v1/watchlist", json={"code": "600519", "name": "贵州茅台"})
        resp = client.delete("/api/v1/watchlist/600519")
        assert resp.status_code == 200
        assert resp.json()["message"] == "删除成功"
        assert not any(i["code"] == "600519" for i in resp.json()["watchlist"])

    def test_delete_nonexistent_404(self, client):
        """删除不存在的自选股应返回 404"""
        resp = client.delete("/api/v1/watchlist/NOTEXIST")
        assert resp.status_code == 404
        assert "不在自选股中" in resp.json()["detail"]


class TestWatchlistGroups:
    """GET /api/v1/watchlist/groups — 获取分组列表"""

    def test_empty_groups(self, client):
        """没有自选股时应只有默认分组（或空列表）"""
        resp = client.get("/api/v1/watchlist/groups")
        assert resp.status_code == 200
        # 没有自选股时可能返回空列表或只有默认分组
        groups = resp.json()
        assert isinstance(groups, list)

    def test_groups_after_adding(self, client):
        """添加不同分组的股票后应列出对应分组"""
        client.post("/api/v1/watchlist", json={"code": "600519", "name": "贵州茅台", "group": "白酒"})
        client.post("/api/v1/watchlist", json={"code": "000001", "name": "平安银行", "group": "银行"})
        client.post("/api/v1/watchlist", json={"code": "000858", "name": "五粮液", "group": "白酒"})

        resp = client.get("/api/v1/watchlist/groups")
        groups = resp.json()
        assert "白酒" in groups
        assert "银行" in groups


class TestCreateGroup:
    """POST /api/v1/watchlist/group — 创建分组"""

    def test_create_new_group(self, client):
        """创建新分组应成功"""
        resp = client.post("/api/v1/watchlist/group", json={"name": "科技"})
        assert resp.status_code == 200
        assert "创建成功" in resp.json()["message"]

    def test_create_duplicate_group(self, client):
        """创建已存在的分组应返回已存在提示"""
        client.post("/api/v1/watchlist/group", json={"name": "科技"})
        resp = client.post("/api/v1/watchlist/group", json={"name": "科技"})
        assert resp.status_code == 200
        assert "已存在" in resp.json()["message"]


class TestDeleteGroup:
    """DELETE /api/v1/watchlist/group/{name} — 删除分组"""

    def test_delete_group_moves_items_to_default(self, client):
        """删除分组后该分组下的股票应移到默认分组"""
        client.post("/api/v1/watchlist", json={"code": "600519", "name": "贵州茅台", "group": "白酒"})
        client.post("/api/v1/watchlist", json={"code": "000858", "name": "五粮液", "group": "白酒"})

        resp = client.delete("/api/v1/watchlist/group/白酒")
        assert resp.status_code == 200
        assert "已删除" in resp.json()["message"]

        # 确认股票已移到默认分组
        watchlist = client.get("/api/v1/watchlist").json()
        for item in watchlist:
            assert item["group"] == "默认"

    def test_delete_nonexistent_group_404(self, client):
        """删除不存在的分组应返回 404"""
        resp = client.delete("/api/v1/watchlist/group/不存在的分组")
        assert resp.status_code == 404

    def test_delete_default_group_400(self, client):
        """删除默认分组应返回 400"""
        resp = client.delete("/api/v1/watchlist/group/默认")
        assert resp.status_code == 400
        assert "不能删除默认分组" in resp.json()["detail"]
