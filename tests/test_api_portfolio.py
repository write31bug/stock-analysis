"""持仓数据接口测试"""

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app

TEST_XLSX_PATH = "/workspace/.uploads/1a18587b-bd29-41ff-8d5a-52d8d5a4325d_汇总持仓.xlsx"


@pytest.fixture
def client():
    """创建测试客户端，触发 lifespan 事件"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_portfolio(client):
    """每个测试前后清空持仓数据，保证测试独立性"""
    client.delete("/api/portfolio")
    yield
    client.delete("/api/portfolio")


class TestGetPortfolioEmpty:
    """GET /api/portfolio — 空持仓"""

    def test_get_portfolio_empty(self, client):
        """无数据时应返回空列表"""
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        assert resp.json() == []


class TestImportPortfolio:
    """POST /api/portfolio/import — 导入持仓"""

    def test_import_portfolio(self, client):
        """导入 xlsx 文件应成功，验证 50 条记录"""
        with open(TEST_XLSX_PATH, "rb") as f:
            resp = client.post(
                "/api/portfolio/import",
                files={
                    "file": ("汇总持仓.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] == 50

        # 验证数据库中确实有 50 条
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        assert len(resp.json()) == 50

    def test_import_portfolio_summary_fields(self, client):
        """导入后验证特定记录的字段值正确"""
        with open(TEST_XLSX_PATH, "rb") as f:
            client.post(
                "/api/portfolio/import",
                files={
                    "file": ("汇总持仓.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                },
            )

        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 50

        # 每条记录都应有 code 和 name
        for item in items:
            assert item["code"] is not None and item["code"] != ""
            assert "hold_amount" in item
            assert "day_pnl" in item
            assert "latest_price" in item

    def test_import_portfolio_skips_summary_row(self, client):
        """汇总行（代码为 '汇总' 或 '合计'）应被跳过"""
        with open(TEST_XLSX_PATH, "rb") as f:
            resp = client.post(
                "/api/portfolio/import",
                files={
                    "file": ("汇总持仓.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                },
            )
        assert resp.status_code == 200
        data = resp.json()

        # 验证没有汇总行被导入
        resp = client.get("/api/portfolio")
        items = resp.json()
        codes = [item["code"] for item in items]
        assert "汇总" not in codes
        assert "合计" not in codes
        # skipped 应大于 0（至少有汇总行被跳过）
        assert data["skipped"] >= 1

    def test_import_portfolio_csv(self, client):
        """导入 CSV 文件应成功"""
        df = pd.DataFrame(
            {
                "代码": ["600519", "000001"],
                "名称": ["贵州茅台", "平安银行"],
                "持有金额": ["1000", "2000"],
                "当日盈亏": ["10.5", "-5.3"],
                "最新价": ["1800.0", "12.5"],
            }
        )
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        resp = client.post(
            "/api/portfolio/import",
            files={"file": ("test.csv", buffer, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] == 2

        # 验证数据
        resp = client.get("/api/portfolio")
        items = resp.json()
        assert len(items) == 2
        codes = {item["code"] for item in items}
        assert codes == {"600519", "000001"}

        # 验证具体字段值
        for item in items:
            if item["code"] == "600519":
                assert item["name"] == "贵州茅台"
                assert item["hold_amount"] == 1000.0
                assert item["day_pnl"] == 10.5
                assert item["latest_price"] == 1800.0
            elif item["code"] == "000001":
                assert item["name"] == "平安银行"
                assert item["hold_amount"] == 2000.0

    def test_import_portfolio_invalid_file(self, client):
        """上传非支持格式的文件应返回 400"""
        buffer = io.BytesIO(b"this is not a valid spreadsheet")
        resp = client.post(
            "/api/portfolio/import",
            files={"file": ("test.txt", buffer, "text/plain")},
        )
        assert resp.status_code == 400
        assert "仅支持" in resp.json()["detail"]

    def test_import_portfolio_missing_code_column(self, client):
        """xlsx 文件缺少 '代码' 列应返回 400"""
        df = pd.DataFrame(
            {
                "名称": ["贵州茅台", "平安银行"],
                "持有金额": ["1000", "2000"],
            }
        )
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        resp = client.post(
            "/api/portfolio/import",
            files={"file": ("test.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 400
        assert "未找到" in resp.json()["detail"] and "代码" in resp.json()["detail"]


class TestGetPortfolioSummary:
    """GET /api/portfolio/summary — 持仓汇总"""

    def test_get_portfolio_summary(self, client):
        """导入后获取汇总，验证 total_amount、count 等字段"""
        df = pd.DataFrame(
            {
                "代码": ["600519", "000001", "000858"],
                "名称": ["贵州茅台", "平安银行", "五粮液"],
                "持有金额": ["10000", "20000", "5000"],
                "当日盈亏": ["100", "-50", "30"],
                "持有盈亏": ["500", "-200", "150"],
                "今年盈亏": ["1000", "-500", "300"],
            }
        )
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        client.post(
            "/api/portfolio/import",
            files={"file": ("test.csv", buffer, "text/csv")},
        )

        resp = client.get("/api/portfolio/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert data["total_amount"] == 35000.0
        assert data["total_day_pnl"] == 80.0
        assert data["total_hold_pnl"] == 450.0
        assert data["total_year_pnl"] == 800.0
        # day_pnl_pct 应为 80/35000*100
        assert abs(data["day_pnl_pct"] - (80.0 / 35000.0 * 100)) < 0.01


class TestDeletePortfolioItem:
    """DELETE /api/portfolio/{code} — 删除单条持仓"""

    def test_delete_portfolio_item(self, client):
        """删除存在的持仓项应成功"""
        # 先导入
        df = pd.DataFrame(
            {
                "代码": ["600519", "000001"],
                "名称": ["贵州茅台", "平安银行"],
                "持有金额": ["1000", "2000"],
            }
        )
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        client.post(
            "/api/portfolio/import",
            files={"file": ("test.csv", buffer, "text/csv")},
        )

        # 删除一条
        resp = client.delete("/api/portfolio/600519")
        assert resp.status_code == 200
        assert "600519" in resp.json()["message"]

        # 验证只剩一条
        resp = client.get("/api/portfolio")
        items = resp.json()
        assert len(items) == 1
        assert items[0]["code"] == "000001"

    def test_delete_portfolio_not_found(self, client):
        """删除不存在的持仓项应返回 404"""
        resp = client.delete("/api/portfolio/NOTEXIST")
        assert resp.status_code == 404
        assert "不在持仓中" in resp.json()["detail"]


class TestClearPortfolio:
    """DELETE /api/portfolio — 清空全部持仓"""

    def test_clear_portfolio(self, client):
        """清空后应返回空列表"""
        # 先导入
        df = pd.DataFrame(
            {
                "代码": ["600519", "000001"],
                "名称": ["贵州茅台", "平安银行"],
                "持有金额": ["1000", "2000"],
            }
        )
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        client.post(
            "/api/portfolio/import",
            files={"file": ("test.csv", buffer, "text/csv")},
        )

        # 清空
        resp = client.delete("/api/portfolio")
        assert resp.status_code == 200
        assert "已清空" in resp.json()["message"]
        assert resp.json()["message"].strip().endswith("2 条持仓")

        # 验证为空
        resp = client.get("/api/portfolio")
        assert resp.json() == []


class TestImportPortfolioUpsert:
    """POST /api/portfolio/import — 增量更新模式"""

    def test_import_portfolio_upsert(self, client):
        """导入两次，第二次应为更新（增量更新模式）"""
        with open(TEST_XLSX_PATH, "rb") as f:
            file_content = f.read()

        # 第一次导入：全部新增
        resp1 = client.post(
            "/api/portfolio/import",
            files={
                "file": (
                    "汇总持仓.xlsx",
                    io.BytesIO(file_content),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert resp1.status_code == 200
        assert resp1.json()["added"] == 50
        assert resp1.json()["updated"] == 0

        # 第二次导入：全部更新
        resp2 = client.post(
            "/api/portfolio/import",
            files={
                "file": (
                    "汇总持仓.xlsx",
                    io.BytesIO(file_content),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["added"] == 0
        assert resp2.json()["updated"] == 50

        # 验证记录数仍为 50（没有重复）
        resp = client.get("/api/portfolio")
        assert len(resp.json()) == 50
