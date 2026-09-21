from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ExactDecimal, uid, utcnow


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("user_id", "symbol", "exchange", "asset_type"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(256))
    asset_type: Mapped[str] = mapped_column(String(24))
    exchange: Mapped[str] = mapped_column(String(64), default="MANUAL")
    currency: Mapped[str] = mapped_column(String(3))
    sector: Mapped[str | None] = mapped_column(String(128))
    industry: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    cik: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProviderMapping(Base):
    __tablename__ = "provider_mappings"
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    provider_symbol: Mapped[str] = mapped_column(String(128))
    provider_asset_id: Mapped[str] = mapped_column(String(128))


class AssetPrice(Base):
    __tablename__ = "asset_prices"
    __table_args__ = (UniqueConstraint("asset_id", "date", "provider"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    open: Mapped[Decimal | None] = mapped_column(ExactDecimal)
    high: Mapped[Decimal | None] = mapped_column(ExactDecimal)
    low: Mapped[Decimal | None] = mapped_column(ExactDecimal)
    close: Mapped[Decimal] = mapped_column(ExactDecimal)
    volume: Mapped[Decimal | None] = mapped_column(ExactDecimal)
    provider: Mapped[str] = mapped_column(String(32))
    adjustment: Mapped[str] = mapped_column(String(24), default="raw")
    valuation_basis: Mapped[str | None] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiCache(Base):
    __tablename__ = "api_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[Any] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    day: Mapped[str] = mapped_column(String(10))
    month: Mapped[str] = mapped_column(String(7))
    daily_count: Mapped[int] = mapped_column(Integer, default=0)
    monthly_count: Mapped[int] = mapped_column(Integer, default=0)
    minute_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    minute_count: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    last_request: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    comment: Mapped[str] = mapped_column(Text, default="")


class WatchlistAsset(Base):
    __tablename__ = "watchlist_assets"
    watchlist_id: Mapped[str] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(String(500), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
