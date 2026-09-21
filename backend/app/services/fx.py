from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.portfolio import FXRate
from app.providers.base import ProviderError
from app.providers.gateway import Gateway


@dataclass(frozen=True)
class FXConversion:
    rate: Decimal
    provider: str
    effective_at: datetime
    precision: str


_FMP_INTRADAY_UNAVAILABLE = False


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

    def get_at(
        self,
        user_id: str,
        base: str,
        quote: str,
        executed_at: datetime,
        manual_rate: Decimal | None = None,
    ) -> FXConversion | None:
        """Use an hourly candle when available, otherwise an auditable ECB daily rate."""
        if executed_at.tzinfo is None:
            executed_at = executed_at.replace(tzinfo=UTC)
        else:
            executed_at = executed_at.astimezone(UTC)
        if base == quote:
            return FXConversion(Decimal(1), "identity", executed_at, "exact")
        if manual_rate is not None:
            return FXConversion(manual_rate, "manual", executed_at, "exact")

        global _FMP_INTRADAY_UNAVAILABLE
        if settings.fmp_api_key and not _FMP_INTRADAY_UNAVAILABLE:
            try:
                result = Gateway(self.db).get(
                    "fmp",
                    "https://financialmodelingprep.com/stable/historical-chart/1hour",
                    {
                        "symbol": f"{base}{quote}",
                        "from": (executed_at.date() - timedelta(days=1)).isoformat(),
                        "to": executed_at.date().isoformat(),
                        "apikey": settings.fmp_api_key,
                    },
                    ttl=settings.history_ttl,
                )
                candidates: list[tuple[datetime, Decimal]] = []
                for row in result.data if isinstance(result.data, list) else []:
                    timestamp = datetime.fromisoformat(str(row["date"]).replace("Z", "+00:00"))
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=UTC)
                    else:
                        timestamp = timestamp.astimezone(UTC)
                    rate = Decimal(str(row["close"]))
                    if timestamp <= executed_at and rate > 0:
                        candidates.append((timestamp, rate))
                if candidates:
                    timestamp, rate = max(candidates, key=lambda item: item[0])
                    if executed_at - timestamp <= timedelta(hours=2):
                        return FXConversion(rate, "fmp_hourly", timestamp, "hourly")
            except (ProviderError, KeyError, ValueError, TypeError):
                _FMP_INTRADAY_UNAVAILABLE = True

        rate = self.get(user_id, base, quote, executed_at.date(), fetch=True)
        if rate is None:
            return None
        source = self.db.scalar(
            select(FXRate)
            .where(
                FXRate.user_id == user_id,
                FXRate.base == base,
                FXRate.quote == quote,
                FXRate.date <= executed_at.date(),
                FXRate.date >= executed_at.date() - timedelta(days=7),
            )
            .order_by(FXRate.date.desc())
        )
        if source is None:
            source = self.db.scalar(
                select(FXRate)
                .where(
                    FXRate.user_id == user_id,
                    FXRate.base == quote,
                    FXRate.quote == base,
                    FXRate.date <= executed_at.date(),
                    FXRate.date >= executed_at.date() - timedelta(days=7),
                )
                .order_by(FXRate.date.desc())
            )
        effective_date = source.date if source else executed_at.date()
        return FXConversion(
            rate,
            source.provider if source else "frankfurter_ecb",
            datetime.combine(effective_date, datetime.min.time(), tzinfo=UTC),
            "daily",
        )

    def ensure_history(
        self,
        user_id: str,
        base: str,
        quote: str,
        start: date,
        end: date,
    ) -> None:
        if base == quote:
            return
        coverage = self.db.execute(
            select(func.min(FXRate.date), func.max(FXRate.date)).where(
                FXRate.user_id == user_id,
                FXRate.base == base,
                FXRate.quote == quote,
                FXRate.date >= start,
                FXRate.date <= end,
            )
        ).one()
        if coverage[0] and coverage[0] <= start + timedelta(days=7) and coverage[1] >= end - timedelta(days=7):
            return
        try:
            response = Gateway(self.db).get(
                "frankfurter",
                "https://api.frankfurter.dev/v2/rates",
                {
                    "base": base.lower(),
                    "quotes": quote.lower(),
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "providers": "ecb",
                },
                ttl=settings.profile_ttl,
            )
            for row in response.data if isinstance(response.data, list) else []:
                if str(row.get("quote", "")).upper() != quote:
                    continue
                self.db.merge(
                    FXRate(
                        user_id=user_id,
                        base=base,
                        quote=quote,
                        date=date.fromisoformat(row["date"]),
                        rate=Decimal(str(row["rate"])),
                        provider="frankfurter_ecb",
                        retrieved_at=response.retrieved_at,
                    )
                )
            self.db.commit()
        except (ProviderError, KeyError, ValueError, TypeError):
            self.db.rollback()
