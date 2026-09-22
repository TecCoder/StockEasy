from datetime import date
from decimal import Decimal as D

import pytest

from app.analytics.growth import cagr
from app.analytics.valuation import (
    EPSObservation,
    discrete_quarterly_eps,
    fcf,
    fcf_yield,
    historical_pe,
    pe,
    ttm_eps,
)
from app.models import AssetPrice, FundamentalFact
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


def test_cumulative_eps_is_converted_to_discrete_quarters():
    cumulative = [
        EPSObservation(
            date(2024, 1, 1), date(2024, 3, 31), date(2024, 5, 1), D(1), "q1", basis="sec"
        ),
        EPSObservation(
            date(2024, 1, 1), date(2024, 6, 30), date(2024, 8, 1), D(3), "h1", basis="sec"
        ),
        EPSObservation(
            date(2024, 1, 1), date(2024, 9, 30), date(2024, 11, 1), D(6), "m9", basis="sec"
        ),
        EPSObservation(
            date(2024, 1, 1), date(2024, 12, 31), date(2025, 2, 1), D(10), "fy", basis="sec"
        ),
    ]

    quarters = discrete_quarterly_eps(cumulative)

    assert [quarter.value for quarter in sorted(quarters, key=lambda value: value.end)] == [
        D(1),
        D(2),
        D(3),
        D(4),
    ]
    assert ttm_eps(quarters, date(2025, 2, 2), "USD", "sec")[0] == 10


def test_valuation_endpoint_returns_daily_pe(auth, db):
    asset = auth.post(
        "/api/assets",
        json={
            "symbol": "TEST",
            "name": "Test Company",
            "currency": "USD",
            "asset_type": "STOCK",
            "exchange": "NASDAQ",
        },
    ).json()
    for index, observation in enumerate(observations()):
        db.add(
            FundamentalFact(
                id=f"eps-{index}",
                asset_id=asset["id"],
                concept="eps",
                taxonomy="us-gaap",
                source_concept="EarningsPerShareDiluted",
                unit="USD/shares",
                value=observation.value,
                start=observation.start,
                end=observation.end,
                filed=observation.filed,
                accession=observation.accession,
                fiscal_period=f"Q{index + 1}",
                provider="sec",
            )
        )
    db.add(
        AssetPrice(
            asset_id=asset["id"],
            date=date(2025, 2, 3),
            currency="USD",
            close=D(100),
            provider="manual",
            adjustment="raw",
        )
    )
    db.commit()

    result = auth.get(f"/api/assets/{asset['id']}/valuation")

    assert result.status_code == 200
    assert D(result.json()["current_pe"]) == 10
    assert result.json()["historical_pe"][0]["date"] == "2025-02-03"


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
