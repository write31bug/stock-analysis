"""定时采集调度器测试"""

import threading
import time
from unittest.mock import MagicMock, patch

from backend.scheduler import (
    _get_watchlist_codes,
    _save_to_db,
    get_scheduler_state,
    run_collect_once,
    start_scheduler,
    stop_scheduler,
)


class TestGetSchedulerState:
    """get_scheduler_state — 返回调度器状态字典"""

    def test_returns_dict_with_expected_keys(self):
        """返回的字典应包含 running, last_run, interval 等键"""
        state = get_scheduler_state()
        assert isinstance(state, dict)
        expected_keys = {
            "running",
            "last_run",
            "last_status",
            "next_run",
            "interval",
            "total_collected",
            "total_failed",
        }
        assert expected_keys.issubset(state.keys())

    def test_returns_copy_not_reference(self):
        """返回的应是副本，修改不影响内部状态"""
        state1 = get_scheduler_state()
        state1["running"] = True
        state2 = get_scheduler_state()
        # 内部状态不应被外部修改影响
        assert state2["running"] is False


class TestGetWatchlistCodes:
    """_get_watchlist_codes — 从配置文件读取自选股代码列表"""

    @patch("stock_analysis.config.load_config")
    def test_string_items(self, mock_load_config):
        """watchlist 中字符串项应直接作为代码"""
        mock_load_config.return_value = {
            "watchlist": ["600519", "000001", "000858"],
        }
        codes = _get_watchlist_codes()
        assert codes == ["600519", "000001", "000858"]

    @patch("stock_analysis.config.load_config")
    def test_dict_items(self, mock_load_config):
        """watchlist 中字典项应提取 code 字段"""
        mock_load_config.return_value = {
            "watchlist": [
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000001", "name": "平安银行"},
            ],
        }
        codes = _get_watchlist_codes()
        assert codes == ["600519", "000001"]

    @patch("stock_analysis.config.load_config")
    def test_mixed_items(self, mock_load_config):
        """watchlist 中混合字符串和字典项应都能正确提取"""
        mock_load_config.return_value = {
            "watchlist": [
                "600519",
                {"code": "000001", "name": "平安银行"},
                "000858",
            ],
        }
        codes = _get_watchlist_codes()
        assert codes == ["600519", "000001", "000858"]

    @patch("stock_analysis.config.load_config")
    def test_get_watchlist_codes_empty(self, mock_load_config):
        """配置中 watchlist 为空列表时应返回空列表"""
        mock_load_config.return_value = {"watchlist": []}
        codes = _get_watchlist_codes()
        assert codes == []

    @patch("stock_analysis.config.load_config")
    def test_filters_blank_codes(self, mock_load_config):
        """应过滤掉空白代码"""
        mock_load_config.return_value = {
            "watchlist": ["600519", "", "  ", {"code": ""}, {"code": "  "}, "000001"],
        }
        codes = _get_watchlist_codes()
        assert codes == ["600519", "000001"]

    @patch("stock_analysis.config.load_config")
    def test_no_watchlist_key(self, mock_load_config):
        """配置中没有 watchlist 键时应返回空列表"""
        mock_load_config.return_value = {}
        codes = _get_watchlist_codes()
        assert codes == []


class TestSaveToDb:
    """_save_to_db — 将分析结果存入数据库"""

    def _make_mock_db(self):
        """创建模拟数据库会话"""
        db = MagicMock()
        db.query.return_value.filter.return_value.delete.return_value = 0
        return db

    def test_save_to_db(self):
        """正常结果应创建 AnalysisRecord 并提交"""
        db = self._make_mock_db()
        result = {
            "stock_info": {
                "code": "600519",
                "name": "贵州茅台",
                "market": "sh",
                "asset_type": "stock",
                "current_price": 1800.0,
                "change_pct": 1.5,
            },
            "analysis": {
                "score": 75,
                "trend": "上涨",
                "recommendation": "买入",
                "summary": "测试摘要",
            },
            "technical_indicators": {"ma5": 1750.0, "ma20": 1700.0},
        }

        _save_to_db(db, result)

        # 验证使用 merge 而非先删后插
        db.merge.assert_called_once()
        # 验证不再调用 delete
        db.query.return_value.filter.return_value.delete.assert_not_called()
        # 验证不再调用 add（改用 merge）
        db.add.assert_not_called()
        record = db.merge.call_args[0][0]
        assert record.code == "600519"
        assert record.name == "贵州茅台"
        assert record.score == 75
        assert record.trend == "上涨"
        assert record.recommendation == "买入"
        assert record.current_price == 1800.0
        assert record.change_pct == 1.5
        assert record.summary == "测试摘要"
        assert record.indicators_json is not None

    def test_save_to_db_error_result(self):
        """包含 error 键的结果不应保存"""
        db = self._make_mock_db()
        result = {
            "error": "网络超时",
            "stock_info": {"code": "600519"},
        }

        _save_to_db(db, result)

        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_save_to_db_empty_code(self):
        """code 为空时不应保存"""
        db = self._make_mock_db()
        result = {
            "stock_info": {"code": ""},
            "analysis": {"score": 50},
        }

        _save_to_db(db, result)

        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_save_to_db_missing_stock_info(self):
        """缺少 stock_info 时不应保存"""
        db = self._make_mock_db()
        result = {
            "analysis": {"score": 50},
        }

        _save_to_db(db, result)

        db.add.assert_not_called()
        db.commit.assert_not_called()


class TestRunCollectOnce:
    """run_collect_once — 执行一次采集"""

    @patch("backend.scheduler._save_to_db")
    @patch("backend.scheduler._analyze_one")
    @patch("backend.scheduler._get_watchlist_codes")
    def test_run_collect_once(self, mock_codes, mock_analyze, mock_save):
        """正常采集应返回正确的 collected 和 failed 计数"""
        mock_codes.return_value = ["600519", "000001", "000858"]
        mock_analyze.side_effect = [
            {"stock_info": {"code": "600519"}, "analysis": {"score": 70}},
            {"error": "超时", "stock_info": {"code": "000001"}},
            {"stock_info": {"code": "000858"}, "analysis": {"score": 80}},
        ]

        with patch("backend.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            result = run_collect_once()

        assert result["collected"] == 2
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "000001"

    @patch("backend.scheduler._get_watchlist_codes")
    def test_run_collect_once_empty_watchlist(self, mock_codes):
        """自选股列表为空时应返回提示消息"""
        mock_codes.return_value = []

        result = run_collect_once()

        assert result["collected"] == 0
        assert result["failed"] == 0
        assert "自选股列表为空" in result["message"]

    @patch("backend.scheduler._save_to_db")
    @patch("backend.scheduler._analyze_one")
    @patch("backend.scheduler._get_watchlist_codes")
    def test_run_collect_once_all_fail(self, mock_codes, mock_analyze, mock_save):
        """所有分析都失败时应正确统计 failed 数量"""
        mock_codes.return_value = ["600519", "000001"]
        mock_analyze.side_effect = [
            {"error": "网络错误", "stock_info": {"code": "600519"}},
            {"error": "数据缺失", "stock_info": {"code": "000001"}},
        ]

        with patch("backend.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            result = run_collect_once()

        assert result["collected"] == 0
        assert result["failed"] == 2
        assert len(result["errors"]) == 2
        # 不应调用 _save_to_db
        mock_save.assert_not_called()

    @patch("backend.scheduler._save_to_db")
    @patch("backend.scheduler._analyze_one")
    @patch("backend.scheduler._get_watchlist_codes")
    def test_run_collect_once_exception_in_analyze(self, mock_codes, mock_analyze, mock_save):
        """_analyze_one 抛异常时应计入 failed"""
        mock_codes.return_value = ["600519"]
        mock_analyze.side_effect = RuntimeError("unexpected crash")

        with patch("backend.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            result = run_collect_once()

        assert result["collected"] == 0
        assert result["failed"] == 1
        assert result["errors"][0]["code"] == "600519"


class TestStartStopScheduler:
    """start_scheduler / stop_scheduler — 调度器线程管理"""

    def setup_method(self):
        """每个测试前确保调度器已停止"""
        stop_scheduler()
        # 等待已有 scheduler 线程完全退出
        for _ in range(20):
            threads = [t for t in threading.enumerate() if t.name == "scheduler" and t.is_alive()]
            if not threads:
                break
            time.sleep(0.1)

    def teardown_method(self):
        """每个测试后确保调度器已停止"""
        stop_scheduler()

    def test_start_stop_scheduler(self):
        """启动后 running=True，停止后 running=False"""
        start_scheduler(interval=300)
        time.sleep(0.2)

        state = get_scheduler_state()
        assert state["running"] is True
        assert state["interval"] == 300

        stop_scheduler()
        time.sleep(0.2)

        state = get_scheduler_state()
        assert state["running"] is False

    def test_start_scheduler_idempotent(self):
        """重复启动不应创建多个线程"""
        stop_scheduler()  # 确保先停止
        time.sleep(1)  # 等待线程完全退出

        start_scheduler(interval=300)
        time.sleep(0.5)

        # 记录当前活跃的 scheduler 线程数
        threads_before = [t for t in threading.enumerate() if t.name == "scheduler" and t.is_alive()]
        assert len(threads_before) == 1

        # 再次启动（应被忽略）
        start_scheduler(interval=600)
        time.sleep(0.3)

        threads_after = [t for t in threading.enumerate() if t.name == "scheduler" and t.is_alive()]
        assert len(threads_after) == 1

        # interval 不应被覆盖
        state = get_scheduler_state()
        assert state["interval"] == 300

        stop_scheduler()
        time.sleep(0.2)
