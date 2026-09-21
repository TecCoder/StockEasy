from datetime import date
from decimal import Decimal as D

import pytest

from app.analytics.growth import cagr
from app.analytics.valuation import EPSObservation, fcf, fcf_yield, historical_pe, pe, ttm_eps
from app.services.sector import SectorValuationService


def observations():
    return [
        EPSObservation(
            date(2024, 1, 1), date(2024, 3, 31), date(2024, 5, 1), D(1), "q1", basis="verified"
        ),
        EPSObservation(
            date(2024, 4, 1), date(2024, 6, 30), date(2024, 8, 1), D(2), "q2", basis="verified"
        ),
        EPSObservation(
            date(2024, 7, 1), date(2024, 9, 30), date(2024, 11, 1), D(3), "q3", basis="verified"
        ),
        EPSObservation(
            date(2024, 10, 1), date(2024, 12, 31), date(2025, 2, 1), D(4), "q4", basis="verified"
        ),
    ]


def test_fundamental_formulas():
    assert fcf(D(100), D(30)) == 70
    assert fcf_yield(D(-20), D(200)) == D("-.1")
    assert fcf_yield(D(1), D(0)) is None
    assert pe(D(100), D(-1)) is None
    assert pe(D(100), D(4)) == 25
    assert cagr(D(100), D(121), 2) == pytest.approx(0.1)
    assert cagr(D(-1), D(1), 5) is None


def test_point_in_time_eps_missing_quarters_and_share_basis():
    obs = observations()
    assert ttm_eps(obs, date(2025, 2, 1), "USD", "verified")[0] is None
    assert ttm_eps(obs, date(2025, 2, 2), "USD", "verified")[0] == 10
    assert ttm_eps(obs[:3], date(2025, 2, 2), "USD", "verified")[0] is None
    assert ttm_eps(obs, date(2025, 2, 2), "USD", None)[0] is None
    assert ttm_eps(obs, date(2025, 2, 2), "EUR", "verified")[0] is None
    obs.append(
        EPSObservation(
            date(2024, 1, 1),
            date(2024, 3, 31),
            date(2025, 3, 1),
            D(9),
            "restatement",
            basis="verified",
        )
    )
    result = historical_pe(
        [(date(2025, 2, 2), D(100)), (date(2025, 3, 2), D(100))], obs, "USD", "verified"
    )
    assert result[0]["pe"] == 10
    assert result[1]["pe"] == D(100) / 18


def test_sector_requires_real_universe_and_sample_size():
    service = SectorValuationService()
    assert (
        service.aggregate({"A": 10, "B": -3, "C": None}, "2025-01-01", "u", "manual")["median_pe"]
        is None
    )
    r = service.aggregate(
        {"A": 10, "B": 20, "C": 30, "D": 40, "E": 1000}, "2025-01-01", "u", "manual"
    )
    assert r["median_pe"] == 30 and r["sample_size"] == 5
