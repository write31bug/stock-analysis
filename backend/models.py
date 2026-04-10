"""SQLAlchemy ORM 模型"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    market: Mapped[str] = mapped_column(String(20), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(10), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    trend: Mapped[str] = mapped_column(String(20), nullable=True)
    recommendation: Mapped[str] = mapped_column(String(100), nullable=True)
    current_price: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)
    change_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    indicators_json: Mapped[str] = mapped_column(Text, nullable=True)
    analysis_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("idx_code_time", "code", "analysis_time", unique=True),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "market": self.market,
            "asset_type": self.asset_type,
            "score": self.score,
            "trend": self.trend,
            "recommendation": self.recommendation,
            "current_price": self.current_price,
            "change_pct": self.change_pct,
            "summary": self.summary,
            "analysis_time": self.analysis_time.isoformat() if self.analysis_time else None,
        }


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    condition_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_value: Mapped[float] = mapped_column(Numeric(18,4), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)
    triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("uq_alert_code_cond_val", "code", "condition_type", "target_value", unique=True),)


class Portfolio(Base):
    """持仓数据表"""

    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    hold_amount: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 持有金额
    day_pnl: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 当日盈亏
    day_pnl_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 当日盈亏率
    hold_pnl: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 持有盈亏
    hold_pnl_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 持有盈亏率
    total_pnl: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 累计盈亏
    total_pnl_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 累计盈亏率
    week_pnl: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 本周盈亏
    month_pnl: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 本月盈亏
    year_pnl: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 今年盈亏
    position_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 仓位占比
    hold_quantity: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 持有数量
    hold_days: Mapped[int] = mapped_column(Integer, nullable=True)  # 持仓天数
    latest_change_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 最新涨幅
    latest_price: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 最新价
    unit_cost: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 单位成本
    breakeven_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 回本涨幅
    month_1_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 近1月涨幅
    month_3_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 近3月涨幅
    month_6_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 近6月涨幅
    year_1_pct: Mapped[float] = mapped_column(Numeric(18,4), nullable=True)  # 近1年涨幅
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )  # 导入时间（首次创建）
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )  # 分析时间（分析成功时更新）

    __table_args__ = (Index("uq_portfolio_code", "code", unique=True),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "hold_amount": self.hold_amount,
            "day_pnl": self.day_pnl,
            "day_pnl_pct": self.day_pnl_pct,
            "hold_pnl": self.hold_pnl,
            "hold_pnl_pct": self.hold_pnl_pct,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": self.total_pnl_pct,
            "week_pnl": self.week_pnl,
            "month_pnl": self.month_pnl,
            "year_pnl": self.year_pnl,
            "position_pct": self.position_pct,
            "hold_quantity": self.hold_quantity,
            "hold_days": self.hold_days,
            "latest_change_pct": self.latest_change_pct,
            "latest_price": self.latest_price,
            "unit_cost": self.unit_cost,
            "breakeven_pct": self.breakeven_pct,
            "month_1_pct": self.month_1_pct,
            "month_3_pct": self.month_3_pct,
            "month_6_pct": self.month_6_pct,
            "year_1_pct": self.year_1_pct,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SystemLog(Base):
    """系统日志表"""

    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # INFO/WARNING/ERROR
    module: Mapped[str] = mapped_column(String(50), nullable=True)  # 模块名
    message: Mapped[str] = mapped_column(Text, nullable=False)  # 日志内容
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Config(Base):
    """配置表"""

    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)  # 存储JSON字符串
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("idx_config_key", "key", unique=True),)
