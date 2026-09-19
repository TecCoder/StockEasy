from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Numeric, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class ExactDecimal(TypeDecorator[Decimal]):
    """Preserve decimal precision on SQLite; use Numeric on PostgreSQL."""

    impl = String(80)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        return dialect.type_descriptor(Numeric(38, 16) if dialect.name != "sqlite" else String(80))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        return str(value) if dialect.name == "sqlite" else value

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        return Decimal(str(value)) if value is not None else None
