"""数据库连接与初始化（默认 MySQL，自动回退 SQLite）"""

import logging
import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# ── 数据库配置 ──────────────────────────────────────────
# 通过环境变量 DATABASE_URL 配置，未配置时使用 SQLite
_FALLBACK_SQLITE_URL = "sqlite:///{}".format(
    os.path.join(os.path.expanduser("~"), ".stock-analysis", "history.db")
)

DATABASE_URL = os.environ.get("DATABASE_URL", _FALLBACK_SQLITE_URL)
_is_sqlite = DATABASE_URL.startswith("sqlite")


# ── SQLite PRAGMA 设置 ───────────────────────────────────
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 连接时设置 WAL 模式和超时"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


# ── 引擎 ────────────────────────────────────────────────
if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        echo=False,
    )
    event.listen(engine, "connect", _set_sqlite_pragma)

else:
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("MySQL 连接成功: %s", DATABASE_URL.split("@")[-1])
    except Exception as e:
        logger.warning("MySQL 连接失败 (%s): %s，回退到 SQLite", DATABASE_URL, e)
        _is_sqlite = True
        DATABASE_URL = _FALLBACK_SQLITE_URL
        engine = create_engine(
            _FALLBACK_SQLITE_URL,
            connect_args={"check_same_thread": False, "timeout": 30},
            echo=False,
        )
        event.listen(engine, "connect", _set_sqlite_pragma)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """初始化数据库（自动建表，表不存在则创建）"""
    if _is_sqlite and "memory" not in DATABASE_URL:
        db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    # create_all 只创建不存在的表，不会删除已有数据
    Base.metadata.create_all(bind=engine)

    db_type = "SQLite" if _is_sqlite else "MySQL"
    # 列出已创建的表
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info("数据库初始化完成 (%s)，已创建表: %s", db_type, ", ".join(tables))


def get_db():
    """获取数据库会话（依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
