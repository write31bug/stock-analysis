"""配置文件管理"""

import json
import os
import threading
from typing import Dict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".stock-analysis")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG: Dict = {
    "watchlist": [],
    "defaults": {
        "market": "auto",
        "days": 60,
        "asset_type": "stock",
    },
}

# 配置文件读写锁
_config_lock = threading.RLock()


def load_config() -> Dict:
    """加载配置文件，不存在则创建默认配置"""
    with _config_lock:
        if not os.path.exists(CONFIG_FILE):
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return DEFAULT_CONFIG.copy()

        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                config = json.load(f)
            # 合并缺失的默认字段
            for key, val in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = val.copy() if isinstance(val, dict) else val
            for key, val in DEFAULT_CONFIG.get("defaults", {}).items():
                if key not in config.get("defaults", {}):
                    config.setdefault("defaults", {})[key] = val
            return config
        except (OSError, json.JSONDecodeError) as e:
            print(f"[WARNING] 配置文件读取失败，使用默认配置: {e}", file=__import__("sys").stderr)
            return DEFAULT_CONFIG.copy()


def save_config(config: Dict) -> None:
    """保存配置文件（原子写入）"""
    with _config_lock:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp_path = CONFIG_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, CONFIG_FILE)
