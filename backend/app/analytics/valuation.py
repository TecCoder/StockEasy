from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, median
from typing import Any


def ratio(
    numerator: Decimal | None, denominator: Decimal | None, positive: bool = False
) -> Decimal | None:
    if (
        numerator is None
        or denominator is None
        or denominator == 0
        or (positive and denominator < 0)
    ):
        return None
    return numerator / denominator


def pe(price: Decimal | None, eps: Decimal | None) -> Decimal | None:
    """Negative/zero earnings have no economically meaningful P/E."""
    return ratio(price, eps, positive=True)


def fcf(operating_cash_flow: Decimal | None, capex: Decimal | None) -> Decimal | None:
    """CapEx input is a positive cash outflow, not a signed statement subtotal."""
    return (
        operating_cash_flow - capex
        if operating_cash_flow is not None and capex is not None
        else None
    )


def fcf_yield(free_cash_flow: Decimal | None, market_cap: Decimal | None) -> Decimal | None:
    return ratio(free_cash_flow, market_cap, positive=True)


@dataclass(frozen=True)
class EPSObservation:
    start: date
    end: date
    filed: date
    value: Decimal
    accession: str
    currency: str = "USD"
    basis: str | None = None


def ttm_eps(
    observations: list[EPSObservation], on: date, currency: str, verified_basis: str | None
) -> tuple[Decimal | None, list[EPSObservation]]:
    """Four consecutive discrete quarters known before on; never use a later restatement."""
    if not verified_basis:
        return None, []
    known: dict[tuple[date, date], EPSObservation] = {}
    for o in sorted(observations, key=lambda x: (x.filed, x.accession)):
        if o.filed >= on or o.currency != currency or o.basis != verified_basis:
            continue
        if 70 <= (o.end - o.start).days <= 105:
            known[(o.start, o.end)] = o
    quarters = sorted(known.values(), key=lambda o: o.end)[-4:]
    if len(quarters) != 4 or (on - quarters[-1].end).days > 180:
        return None, []
    if not 350 <= (quarters[-1].end - quarters[0].start).days <= 380:
        return None, []
    if any(
        b.start != a.end + timedelta(days=1) for a, b in zip(quarters, quarters[1:], strict=False)
    ):
        return None, []
    return sum((o.value for o in quarters), Decimal(0)), quarters


def historical_pe(
    prices: list[tuple[date, Decimal]],
    observations: list[EPSObservation],
    currency: str,
    verified_basis: str | None,
) -> list[dict[str, Any]]:
    result = []
    for day, price in prices:
        eps, inputs = ttm_eps(observations, day, currency, verified_basis)
        result.append(
            {
                "price_date": day,
                "price": price,
                "eps": eps,
                "pe": pe(price, eps),
                "eps_periods": [
                    {"start": o.start, "end": o.end, "filed": o.filed, "accession": o.accession}
                    for o in inputs
                ],
            }
        )
    return result


def valuation_statistics(values: list[float], current: float | None) -> dict[str, float | None]:
    valid = sorted(v for v in values if v > 0)

    def quantile(p: float) -> float | None:
        if not valid:
            return None
        i = (len(valid) - 1) * p
        low = int(i)
        return valid[low] + (valid[min(low + 1, len(valid) - 1)] - valid[low]) * (i - low)

    return {
        "median": median(valid) if valid else None,
        "mean": mean(valid) if valid else None,
        "p25": quantile(0.25),
        "p75": quantile(0.75),
        "percentile": 100 * sum(v <= current for v in valid) / len(valid)
        if valid and current is not None
        else None,
    }
