import math

import pytest

from app.analytics.technical import bollinger, ema, macd, rsi, sma


def test_sma_and_ema_warmup():
    assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4]
    assert ema([1, 2, 3, 8], 3) == [None, None, 2, 5]
    assert sma([1, 2], 200) == [None, None]
    with pytest.raises(ValueError):
        sma([math.inf], 2)


def test_rsi_wilder_reference_and_extremes():
    prices = [
        44.34,
        44.09,
        44.15,
        43.61,
        44.33,
        44.83,
        45.10,
        45.42,
        45.84,
        46.08,
        45.89,
        46.03,
        45.61,
        46.28,
        46.28,
    ]
    assert rsi(prices)[-1] == pytest.approx(70.4641, abs=0.001)
    assert rsi(list(range(20)))[-1] == 100
    assert rsi(list(range(20, 0, -1)))[-1] == 0
    assert rsi([10] * 20)[-1] == 50


def test_macd_linear_series_and_bollinger():
    result = macd(list(range(1, 51)))
    assert result["macd"][25] == pytest.approx(7)
    assert result["signal"][32] is None
    assert result["signal"][33] == pytest.approx(7)
    assert result["histogram"][-1] == pytest.approx(0)
    bands = bollinger([2] * 30)
    assert bands["upper"][-1] == bands["lower"][-1] == 2
