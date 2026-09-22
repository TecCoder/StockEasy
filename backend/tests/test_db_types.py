from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.dialects import postgresql, sqlite

from app.db.base import ExactDecimal


def test_exact_decimal_matches_text_columns_on_sqlite_and_postgresql() -> None:
    value = Decimal("123456789.1234567890123456")
    for dialect in (sqlite.dialect(), postgresql.dialect()):
        column_type = ExactDecimal()
        assert isinstance(column_type.dialect_impl(dialect).impl, String)
        assert column_type.process_bind_param(value, dialect) == str(value)
        assert column_type.process_result_value(str(value), dialect) == value
