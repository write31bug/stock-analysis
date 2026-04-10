"""CLI 命令行接口测试"""

import json
import os
from unittest.mock import patch

import pytest

from stock_analysis.cli import main
from stock_analysis.constants import VERSION


class TestVersion:
    """--version 输出版本号"""

    def test_version(self, capsys):
        """--version 应输出版本号并退出"""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert VERSION in captured.out


class TestCheck:
    """--check 环境自检不崩溃"""

    def test_check(self, capsys):
        """--check 应正常输出自检信息，不抛异常"""
        main(["--check"])
        captured = capsys.readouterr()
        assert "环境自检" in captured.out


class TestSingleTestMode:
    """单只股票 --test 模式"""

    def test_single_test_mode(self, capsys):
        """单只股票 --test 模式应正常输出分析结果"""
        main(["600519", "--test"])
        captured = capsys.readouterr()
        assert "600519" in captured.out


class TestBatchTestMode:
    """批量 --test 模式"""

    def test_batch_test_mode(self, capsys):
        """批量 --test 模式应正常输出多只股票分析结果"""
        main(["--batch", "600519,000001", "--test"])
        captured = capsys.readouterr()
        assert "600519" in captured.out
        assert "000001" in captured.out


class TestJsonOutput:
    """--json --test 输出有效 JSON"""

    def test_json_output(self, capsys):
        """--json --test 应输出可解析的 JSON"""
        main(["600519", "--test", "--json"])
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert "code" in result or "600519" in str(result)


class TestAsciiMode:
    """--ascii --test 不崩溃"""

    def test_ascii_mode(self, capsys):
        """--ascii --test 应正常输出，不抛异常"""
        main(["600519", "--test", "--ascii"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0


class TestWatchlist:
    """持仓管理测试（使用 tmp_path 隔离配置）"""

    def _make_config(self, tmp_path):
        """在 tmp_path 下创建隔离的配置文件"""
        config_file = str(tmp_path / "config.json")
        default = {"watchlist": [], "defaults": {"market": "auto", "days": 60, "asset_type": "stock"}}
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return tmp_path, config_file

    def test_add_to_watchlist(self, tmp_path, capsys):
        """--add 添加到持仓列表"""
        cfg_dir, cfg_file = self._make_config(tmp_path)
        with patch("stock_analysis.cli.CONFIG_FILE", cfg_file), patch(
            "stock_analysis.config.CONFIG_FILE", cfg_file
        ), patch("stock_analysis.config.CONFIG_DIR", str(cfg_dir)):
            main(["--add", "600519"])
            captured = capsys.readouterr()
            assert "已添加" in captured.out
            # 验证配置文件已写入
            with open(cfg_file, encoding="utf-8") as f:
                config = json.load(f)
            assert "600519" in config["watchlist"]

    def test_list_watchlist(self, tmp_path, capsys):
        """--list 显示持仓列表"""
        cfg_dir, cfg_file = self._make_config(tmp_path)
        # 预置数据
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(
                {"watchlist": ["600519", "000001"], "defaults": {"market": "auto", "days": 60, "asset_type": "stock"}},
                f,
                ensure_ascii=False,
                indent=2,
            )
        with patch("stock_analysis.cli.CONFIG_FILE", cfg_file), patch(
            "stock_analysis.config.CONFIG_FILE", cfg_file
        ), patch("stock_analysis.config.CONFIG_DIR", str(cfg_dir)):
            main(["--list"])
            captured = capsys.readouterr()
            assert "600519" in captured.out
            assert "000001" in captured.out

    def test_remove_from_watchlist(self, tmp_path, capsys):
        """--remove 删除持仓"""
        cfg_dir, cfg_file = self._make_config(tmp_path)
        # 预置数据
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(
                {"watchlist": ["600519", "000001"], "defaults": {"market": "auto", "days": 60, "asset_type": "stock"}},
                f,
                ensure_ascii=False,
                indent=2,
            )
        with patch("stock_analysis.cli.CONFIG_FILE", cfg_file), patch(
            "stock_analysis.config.CONFIG_FILE", cfg_file
        ), patch("stock_analysis.config.CONFIG_DIR", str(cfg_dir)):
            main(["--remove", "600519"])
            captured = capsys.readouterr()
            assert "已删除" in captured.out
            # 验证配置文件已更新
            with open(cfg_file, encoding="utf-8") as f:
                config = json.load(f)
            assert "600519" not in config["watchlist"]
            assert "000001" in config["watchlist"]


class TestOutputToFile:
    """-o 输出到文件"""

    def test_output_to_file(self, tmp_path, capsys):
        """-o 应将结果写入指定文件"""
        output_file = str(tmp_path / "result.json")
        main(["600519", "--test", "--json", "-o", output_file])
        captured = capsys.readouterr()
        assert "已保存" in captured.err
        # 验证文件存在且内容有效
        assert os.path.exists(output_file)
        with open(output_file, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 0
        result = json.loads(content)
        assert "code" in result or "600519" in str(result)
