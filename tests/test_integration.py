"""集成测试：验证并发场景下后端不会阻塞"""

import time  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


@pytest.fixture
def client():
    """创建测试客户端，触发 lifespan 事件"""
    with TestClient(app) as c:
        yield c


class TestConcurrentReadWrite:
    """验证后台写入不阻塞前端读取"""

    def test_api_available_during_batch(self, client):
        """批量分析期间，其他API请求不应被阻塞（test模式，无网络请求）"""

        # Submit batch (test mode)
        r = client.post(
            "/api/batch",
            json={
                "codes": ["600519"],
                "days": 60,
                "test": True,
            },
        )
        assert r.status_code == 200
        task_id = r.json()["task_id"]

        # While batch is running, other requests should work
        r = client.get("/api/watchlist")
        assert r.status_code == 200

        r = client.get("/api/health")
        assert r.status_code == 200

        # Wait for batch to complete
        for _ in range(10):
            r = client.get(f"/api/batch/{task_id}")
            if r.json().get("status") == "completed":
                break
            time.sleep(0.2)


class TestSchedulerAPIIntegration:
    """验证 scheduler API 端点"""

    def test_scheduler_status_endpoint(self, client):
        """GET /api/scheduler/status 应返回状态"""
        r = client.get("/api/scheduler/status")
        assert r.status_code == 200
        data = r.json()
        assert "running" in data
        assert "interval" in data


class TestDatabaseSwitching:
    """验证数据库配置切换"""

    def test_test_env_uses_sqlite(self):
        """测试环境应该使用 SQLite 内存数据库"""
        from backend.database import _is_sqlite
        assert _is_sqlite is True

    def test_database_url_from_env(self, monkeypatch):
        """设置环境变量应该切换到 MySQL"""
        import importlib
        from unittest.mock import patch

        monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:123456@localhost:3306/test")
        with patch("sqlalchemy.create_engine") as mock_engine:
            import backend.database as db_mod

            importlib.reload(db_mod)
            assert db_mod._is_sqlite is False
            assert "mysql" in db_mod.DATABASE_URL
