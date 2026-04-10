"""缓存服务"""

import time
from collections import OrderedDict
from typing import Any, Dict, Optional


class CacheService:
    """内存缓存服务"""

    def __init__(self, max_size: int = 1000, expiry_seconds: int = 300):
        """
        初始化缓存服务

        Args:
            max_size: 缓存最大容量
            expiry_seconds: 缓存过期时间（秒）
        """
        self._cache = OrderedDict()
        self._max_size = max_size
        self._expiry_seconds = expiry_seconds

    def _cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        to_remove = []

        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp > self._expiry_seconds:
                to_remove.append(key)

        for key in to_remove:
            self._cache.pop(key, None)

    def _cleanup_oldest(self):
        """清理最旧的缓存，保持缓存大小在限制内"""
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        self._cleanup_expired()

        if key in self._cache:
            value, _ = self._cache[key]
            # 刷新访问时间
            self._cache.move_to_end(key, last=True)
            return value
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self._cleanup_expired()
        self._cleanup_oldest()

        self._cache[key] = (value, time.time())

    def delete(self, key: str) -> None:
        """删除缓存值"""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_size(self) -> int:
        """获取缓存大小"""
        self._cleanup_expired()
        return len(self._cache)


# 全局缓存实例
cache_service = CacheService(max_size=1000, expiry_seconds=300)
