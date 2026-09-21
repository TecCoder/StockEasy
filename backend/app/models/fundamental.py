from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ExactDecimal, utcnow


class FundamentalFact(Base):
    __tablename__ = "fundamental_facts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    concept: Mapped[str] = mapped_column(String(128), index=True)
    taxonomy: Mapped[str] = mapped_column(String(32))
    source_concept: Mapped[str] = mapped_column(String(256))
    unit: Mapped[str] = mapped_column(String(32))
    value: Mapped[Decimal] = mapped_column(ExactDecimal)
    start: Mapped[date | None] = mapped_column(Date)
    end: Mapped[date] = mapped_column(Date, index=True)
    filed: Mapped[date] = mapped_column(Date, index=True)
    accession: Mapped[str] = mapped_column(String(32))
    fiscal_period: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(32), default="sec")
    valuation_basis: Mapped[str | None] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
