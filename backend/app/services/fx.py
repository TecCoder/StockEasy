from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.portfolio import FXRate
from app.providers.base import ProviderError
from app.providers.gateway import Gateway


class FXService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(
        self, user_id: str, base: str, quote: str, on: date, fetch: bool = False
    ) -> Decimal | None:
        if base == quote:
            return Decimal(1)
        row = self.db.scalar(
            select(FXRate)
            .where(
                FXRate.user_id == user_id,
                FXRate.base == base,
                FXRate.quote == quote,
                FXRate.date <= on,
                FXRate.date >= on - timedelta(days=7),
            )
            .order_by(FXRate.date.desc())
        )
        if row:
            return row.rate
        inverse = self.db.scalar(
            select(FXRate)
            .where(
                FXRate.user_id == user_id,
                FXRate.base == quote,
                FXRate.quote == base,
                FXRate.date <= on,
                FXRate.date >= on - timedelta(days=7),
            )
            .order_by(FXRate.date.desc())
        )
        if inverse:
            return Decimal(1) / inverse.rate
        if not fetch:
            return None
        try:
            response = Gateway(self.db).get(
                "frankfurter",
                f"https://api.frankfurter.dev/v2/rate/{base.lower()}/{quote.lower()}",
                {"date": on.isoformat(), "providers": "ecb"},
                ttl=settings.fx_ttl,
            )
            d = response.data
            effective = date.fromisoformat(d["date"])
            rate = Decimal(str(d["rate"]))
            if effective > on or (on - effective).days > 7 or rate <= 0:
                return None
            self.db.merge(
                FXRate(
                    user_id=user_id,
                    base=base,
                    quote=quote,
                    date=effective,
                    rate=rate,
                    provider="frankfurter_ecb",
                    retrieved_at=response.retrieved_at,
                )
            )
            self.db.commit()
            return rate
        except (ProviderError, KeyError, ValueError, TypeError):
            return None
