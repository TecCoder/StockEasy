from decimal import Decimal


def cagr(start: Decimal | None, end: Decimal | None, years: float) -> float | None:
    """CAGR is undefined for a nonpositive base, negative end or invalid horizon."""
    if start is None or end is None or start <= 0 or end < 0 or years <= 0:
        return None
    return (float(end / start) ** (1 / years)) - 1


def yoy(previous: Decimal | None, current: Decimal | None) -> Decimal | None:
    if previous is None or current is None or previous <= 0:
        return None
    return current / previous - 1
