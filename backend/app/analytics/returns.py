import math
from datetime import date
from decimal import Decimal


def xirr(flows: list[tuple[date, Decimal]]) -> float | None:
    """Find a unique annualized root; ambiguous/non-conventional flows return None."""
    combined: dict[date, Decimal] = {}
    for day, amount in flows:
        combined[day] = combined.get(day, Decimal(0)) + amount
    ordered = sorted((d, a) for d, a in combined.items() if a)
    if len(ordered) < 2 or not any(a < 0 for _, a in ordered) or not any(a > 0 for _, a in ordered):
        return None
    # Single sign change is required to avoid reporting one arbitrary root.
    signs = [1 if a > 0 else -1 for _, a in ordered]
    if sum(a != b for a, b in zip(signs, signs[1:], strict=False)) != 1:
        return None
    first = ordered[0][0]

    def npv(log_rate: float) -> float:
        return sum(float(a) * math.exp(-log_rate * (d - first).days / 365) for d, a in ordered)

    lo, hi = -12.0, 12.0
    try:
        if npv(lo) * npv(hi) > 0:
            return None
        for _ in range(150):
            mid = (lo + hi) / 2
            if npv(lo) * npv(mid) <= 0:
                hi = mid
            else:
                lo = mid
        result = math.expm1((lo + hi) / 2)
        return result if math.isfinite(result) else None
    except (OverflowError, ValueError):
        return None


def twr(periods: list[tuple[Decimal, Decimal, Decimal]]) -> Decimal | None:
    """Chain (end - end-of-period external flow)/start; boundary timing must be known."""
    product = Decimal(1)
    for start, end, external_flow in periods:
        if start <= 0:
            return None
        product *= (end - external_flow) / start
    return product - 1 if periods else None
