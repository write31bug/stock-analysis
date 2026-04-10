"""config.py 配置管理模块测试"""

import json

from stock_analysis import config


class TestLoadConfig:
    """load_config 函数测试"""

    def test_load_config_creates_default(self, tmp_path, monkeypatch):
        """首次加载时自动创建默认配置文件"""
        cfg_dir = tmp_path / "cfg"
        cfg_file = cfg_dir / "config.json"
        monkeypatch.setattr(config, "CONFIG_DIR", str(cfg_dir))
        monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))

        result = config.load_config()

        assert cfg_file.exists()
        assert "watchlist" in result
        assert "defaults" in result

    def test_load_config_existing(self, tmp_path, monkeypatch):
        """读取已有配置文件"""
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        cfg_file = cfg_dir / "config.json"
        existing = {"watchlist": ["600519"], "defaults": {"market": "sh", "days": 30, "asset_type": "stock"}}
        cfg_file.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_DIR", str(cfg_dir))
        monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))

        result = config.load_config()

        assert result["watchlist"] == ["600519"]
        assert result["defaults"]["market"] == "sh"
        assert result["defaults"]["days"] == 30

    def test_load_config_merges_missing_keys(self, tmp_path, monkeypatch):
        """旧配置缺少新字段时自动合并"""
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        cfg_file = cfg_dir / "config.json"
        # 旧配置缺少 defaults 中的 asset_type 字段
        old_config = {"watchlist": ["000001"], "defaults": {"market": "sz", "days": 60}}
        cfg_file.write_text(json.dumps(old_config, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_DIR", str(cfg_dir))
        monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))

        result = config.load_config()

        assert result["watchlist"] == ["000001"]
        assert "asset_type" in result["defaults"]
        assert result["defaults"]["asset_type"] == "stock"

    def test_load_config_corrupted(self, tmp_path, monkeypatch):
        """JSON 损坏时返回默认配置（不崩溃）"""
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        cfg_file = cfg_dir / "config.json"
        cfg_file.write_text("{invalid json content!!!", encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_DIR", str(cfg_dir))
        monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))

        result = config.load_config()

        assert "watchlist" in result
        assert "defaults" in result
        assert result["defaults"]["market"] == "auto"

    def test_config_structure(self):
        """默认配置包含 watchlist 和 defaults 键"""
        assert "watchlist" in config.DEFAULT_CONFIG
        assert "defaults" in config.DEFAULT_CONFIG
        assert isinstance(config.DEFAULT_CONFIG["watchlist"], list)
        assert isinstance(config.DEFAULT_CONFIG["defaults"], dict)


class TestSaveConfig:
    """save_config 函数测试"""

    def test_save_config(self, tmp_path, monkeypatch):
        """保存配置到文件"""
        cfg_dir = tmp_path / "cfg"
        cfg_file = cfg_dir / "config.json"
        monkeypatch.setattr(config, "CONFIG_DIR", str(cfg_dir))
        monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))

        new_config = {
            "watchlist": ["600519", "000001"],
            "defaults": {"market": "auto", "days": 90, "asset_type": "stock"},
        }
        config.save_config(new_config)

        assert cfg_file.exists()
        saved = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert saved["watchlist"] == ["600519", "000001"]
        assert saved["defaults"]["days"] == 90
