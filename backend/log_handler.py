"""SQLAlchemy 日志 Handler，将 WARNING+ 日志写入 system_logs 表"""

import collections
import logging
import threading
import time

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import SystemLog


class DBLogHandler(logging.Handler):
    """将 WARNING 及以上日志写入数据库（队列缓冲，批量写入）"""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self._buffer: collections.deque = collections.deque()
        self._lock = threading.Lock()

    def emit(self, record):
        """线程安全地追加日志到缓冲队列"""
        try:
            msg = self.format(record)
            if len(msg) > 2000:
                msg = msg[:2000] + "..."
            with self._lock:
                self._buffer.append({
                    "level": record.levelname,
                    "module": record.name,
                    "message": msg,
                })
        except Exception:
            pass

    def _flush(self):
        """批量将缓冲队列中的日志写入数据库"""
        with self._lock:
            if not self._buffer:
                return
            items = list(self._buffer)
            self._buffer.clear()

        db: Session = SessionLocal()
        try:
            for item in items:
                log = SystemLog(
                    level=item["level"],
                    module=item["module"],
                    message=item["message"],
                )
                db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def _flush_loop(handler: DBLogHandler):
    """定时 flush 线程"""
    while True:
        time.sleep(5)
        try:
            handler._flush()
        except Exception:
            pass


def setup_db_logging():
    """在根 logger 上安装 DB Handler，并启动定时 flush 线程"""
    handler = DBLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)

    flush_thread = threading.Thread(target=_flush_loop, args=(handler,), daemon=True, name="db_log_flush")
    flush_thread.start()
