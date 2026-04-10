"""配置服务 - 数据库存储配置"""

import json
import os
import threading
from typing import Dict, Any

from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import Config

# 默认配置
DEFAULT_CONFIG: Dict = {
    "watchlist": [],
    "defaults": {
        "market": "auto",
        "days": 60,
        "asset_type": "stock",
    },
}

# 配置缓存和锁
_config_cache: Dict[str, Any] = {}
_config_lock = threading.RLock()


def _load_from_db(db: Session) -> Dict[str, Any]:
    """从数据库加载配置"""
    config = DEFAULT_CONFIG.copy()
    config_records = db.query(Config).all()
    
    for record in config_records:
        try:
            key = record.key
            value = json.loads(record.value) if record.value else None
            # 处理嵌套键
            if "." in key:
                parts = key.split(".")
                current = config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                config[key] = value
        except (json.JSONDecodeError, Exception) as e:
            print(f"[WARNING] 加载配置项 {record.key} 失败: {e}")
    
    return config


def _save_to_db(db: Session, config: Dict[str, Any]) -> None:
    """保存配置到数据库"""
    # 扁平化配置
    flat_config = {}
    
    def flatten(d: Dict[str, Any], prefix: str = ""):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                flatten(v, key)
            else:
                flat_config[key] = v
    
    flatten(config)
    
    # 删除旧记录
    db.query(Config).delete()
    
    # 插入新记录
    for key, value in flat_config.items():
        config_record = Config(
            key=key,
            value=json.dumps(value, ensure_ascii=False) if value is not None else None
        )
        db.add(config_record)
    
    db.commit()


def load_config() -> Dict[str, Any]:
    """加载配置，优先从数据库，不存在则初始化默认配置"""
    with _config_lock:
        if _config_cache:
            return _config_cache.copy()
        
        db = SessionLocal()
        try:
            config = _load_from_db(db)
            
            # 如果数据库为空，尝试从旧的文件配置迁移
            if not db.query(Config).first():
                try:
                    from stock_analysis.config import load_config as load_config_from_file
                    file_config = load_config_from_file()
                    if file_config != DEFAULT_CONFIG:
                        config = file_config
                        _save_to_db(db, config)
                except Exception as e:
                    print(f"[WARNING] 从文件迁移配置失败: {e}", file=__import__("sys").stderr)
                    _save_to_db(db, DEFAULT_CONFIG)
                    config = DEFAULT_CONFIG.copy()
            
            _config_cache.update(config)
            return config.copy()
        except Exception as e:
            print(f"[WARNING] 配置加载失败，使用默认配置: {e}", file=__import__("sys").stderr)
            return DEFAULT_CONFIG.copy()
        finally:
            db.close()


def save_config(config: Dict[str, Any]) -> None:
    """保存配置到数据库（原子写入）"""
    with _config_lock:
        db = SessionLocal()
        try:
            _save_to_db(db, config)
            _config_cache.clear()
            _config_cache.update(config)
        except Exception as e:
            db.rollback()
            print(f"[ERROR] 配置保存失败: {e}", file=__import__("sys").stderr)
            raise
        finally:
            db.close()
