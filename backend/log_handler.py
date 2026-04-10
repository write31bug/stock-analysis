"""SQLAlchemy 日志 Handler，将 WARNING+ 日志写入 system_logs 表"""

import logging

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import SystemLog


class DBLogHandler(logging.Handler):
    """将 WARNING 及以上日志写入数据库"""

    def __init__(self):
        super().__init__(level=logging.WARNING)

    def emit(self, record):
        try:
            msg = self.format(record)
            if len(msg) > 2000:
                msg = msg[:2000] + "..."
            db: Session = SessionLocal()
            try:
                log = SystemLog(
                    level=record.levelname,
                    module=record.name,
                    message=msg,
                )
                db.add(log)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        except Exception:
            pass


def setup_db_logging():
    """在根 logger 上安装 DB Handler"""
    handler = DBLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)
