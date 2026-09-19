"""Transparent technical indicators. Warm-up observations are None, never fabricated."""

import math
from statistics import pstdev

Series = list[float | None]


def validate(values: list[float], period: int) -> None:
    if period < 1 or not all(math.isfinite(v) for v in values):
        raise ValueError("Finite observations and a positive period are required")


def sma(values: list[float], period: int) -> Series:
    """Simple rolling mean, with period-1 missing warm-up entries."""
    validate(values, period)
    return [
        sum(values[i - period + 1 : i + 1]) / period if i >= period - 1 else None
        for i in range(len(values))
    ]


def ema(values: list[float], period: int) -> Series:
    """EMA seeded with the first period's SMA; alpha=2/(period+1)."""
    validate(values, period)
    result: Series = [None] * len(values)
    if len(values) < period:
        return result
    current = sum(values[:period]) / period
    result[period - 1] = current
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        current = alpha * values[i] + (1 - alpha) * current
        result[i] = current
    return result


def rsi(values: list[float], period: int = 14) -> Series:
    """Wilder RSI. Flat windows use 50; no losses with gains uses 100."""
    validate(values, period)
    result: Series = [None] * len(values)
    if len(values) <= period:
        return result
    changes = [b - a for a, b in zip(values, values[1:], strict=False)]
    gain = sum(max(0, v) for v in changes[:period]) / period
    loss = sum(max(0, -v) for v in changes[:period]) / period
    for i in range(period, len(values)):
        if i > period:
            gain = (gain * (period - 1) + max(changes[i - 1], 0)) / period
            loss = (loss * (period - 1) + max(-changes[i - 1], 0)) / period
        result[i] = 50 if gain == loss == 0 else 100 if loss == 0 else 100 - 100 / (1 + gain / loss)
    return result


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, Series]:
    """MACD of SMA-seeded EMAs, signal starts after slow+signal-1 observations."""
    a, b = ema(values, fast), ema(values, slow)
    line = [x - y if x is not None and y is not None else None for x, y in zip(a, b, strict=True)]
    valid = [x for x in line if x is not None]
    signal_line = [None] * (len(values) - len(valid)) + ema(valid, signal)
    return {
        "macd": line,
        "signal": signal_line,
        "histogram": [
            x - y if x is not None and y is not None else None
            for x, y in zip(line, signal_line, strict=True)
        ],
    }


def bollinger(values: list[float], period: int = 20, deviations: float = 2) -> dict[str, Series]:
    """Population standard deviation (ddof=0) around a rolling SMA."""
    middle = sma(values, period)
    spread = [
        deviations * pstdev(values[i - period + 1 : i + 1]) if i >= period - 1 else None
        for i in range(len(values))
    ]
    return {
        "middle": middle,
        "upper": [
            m + s if m is not None and s is not None else None
            for m, s in zip(middle, spread, strict=True)
        ],
        "lower": [
            m - s if m is not None and s is not None else None
            for m, s in zip(middle, spread, strict=True)
        ],
    }


def indicators(values: list[float]) -> dict[str, Series]:
    result = {f"SMA{n}": sma(values, n) for n in [20, 50, 100, 200]}
    result.update({f"EMA{n}": ema(values, n) for n in [20, 50, 200]})
    result["RSI14"] = rsi(values)
    result.update({f"MACD_{k}": v for k, v in macd(values).items()})
    result.update({f"BB_{k}": v for k, v in bollinger(values).items()})
    return result
