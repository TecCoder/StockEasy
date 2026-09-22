from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.base import utcnow
from app.models import ApiCache, ProviderMapping, ProviderUsage
from app.providers.base import ProviderError
from app.providers.gateway import Gateway
from app.providers.market import EODHD, TwelveData
from app.providers.sec import SEC


def test_cache_stale_rate_limit_and_secret_exclusion(db):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"price": "12.5"})

    gateway = Gateway(db, httpx.Client(transport=httpx.MockTransport(respond)))
    assert (
        gateway.get("fmp", "https://example.test/quote", {"apikey": "TEST_ONLY"}).data["price"]
        == "12.5"
    )
    gateway.get("fmp", "https://example.test/quote", {"apikey": "TEST_ONLY"})
    assert len(calls) == 1
    cached = db.scalar(select(ApiCache))
    assert "TEST_ONLY" not in cached.key and "TEST_ONLY" not in str(cached.payload)
    cached.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    gateway.client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(429, headers={"Retry-After": "120"}))
    )
    response = gateway.get("fmp", "https://example.test/quote", {"apikey": "TEST_ONLY"})
    assert response.stale and response.warning
    assert db.get(ProviderUsage, "fmp").daily_count == 2
    with pytest.raises(ProviderError):
        gateway.reserve("fmp")


def test_daily_limit_persists(db):
    gateway = Gateway(db)
    usage = gateway.reserve("alpha_vantage")
    usage.daily_count = 25
    db.commit()
    with pytest.raises(ProviderError):
        Gateway(db).reserve("alpha_vantage")


def test_plan_restriction_does_not_block_other_fmp_symbols(db):
    gateway = Gateway(
        db,
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403))),
    )

    with pytest.raises(ProviderError, match="datos no incluidos en el plan"):
        gateway.get("fmp", "https://example.test/quote", {"symbol": "GOOG"})

    usage = db.get(ProviderUsage, "fmp")
    assert usage.retry_after is None


def test_eodhd_fund_search_quote_and_history(db, monkeypatch):
    monkeypatch.setattr(settings, "eodhd_api_key", "TEST_EODHD_ONLY")

    def respond(request):
        assert "TEST_EODHD_ONLY" in str(request.url)
        if "/search/" in request.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "Code": "IE00BDD48S37",
                        "Exchange": "EUFUND",
                        "Name": "Vanguard EUR Corporate 1-3 Year",
                        "Type": "FUND",
                        "Currency": "EUR",
                    }
                ],
            )
        order = request.url.params.get("order")
        rows = [
            {
                "date": "2026-09-18",
                "open": 4.937,
                "high": 4.937,
                "low": 4.937,
                "close": 4.937,
                "adjusted_close": 4.937,
                "volume": 0,
            },
            {
                "date": "2026-09-17",
                "open": 4.9425,
                "high": 4.9425,
                "low": 4.9425,
                "close": 4.9425,
                "adjusted_close": 4.9425,
                "volume": 0,
            },
        ]
        return httpx.Response(200, json=rows if order == "d" else list(reversed(rows)))

    provider = EODHD(Gateway(db, httpx.Client(transport=httpx.MockTransport(respond))))
    search = provider.search_assets("Vanguard")
    assert search.data[0] == {
        "symbol": "IE00BDD48S37",
        "name": "Vanguard EUR Corporate 1-3 Year",
        "asset_type": "MUTUAL_FUND",
        "exchange": "EUFUND",
        "currency": "EUR",
        "provider": "eodhd",
        "provider_asset_id": "IE00BDD48S37.EUFUND",
    }
    quote = provider.get_quote("IE00BDD48S37.EUFUND", "EUR")
    assert quote.data["price"] == "4.937"
    assert Decimal(quote.data["change_percent"]) < 0
    history = provider.get_historical_prices("IE00BDD48S37.EUFUND", "EUR")
    assert [bar.date.isoformat() for bar in history.data] == ["2026-09-17", "2026-09-18"]
    assert all("TEST_EODHD_ONLY" not in row.key for row in db.scalars(select(ApiCache)))


def test_twelve_data_hourly_history_is_normalized_and_secret_is_not_cached(db, monkeypatch):
    monkeypatch.setattr(settings, "twelve_data_api_key", "TEST_TWELVE_ONLY")
    payload = {
        "meta": {"currency": "USD"},
        "values": [
            {
                "datetime": "2026-09-22 15:00:00",
                "open": "102",
                "high": "104",
                "low": "101",
                "close": "103",
                "volume": "20",
            },
            {
                "datetime": "2026-09-22 14:00:00",
                "open": "100",
                "high": "103",
                "low": "99",
                "close": "102",
                "volume": "10",
            },
        ],
        "status": "ok",
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )

    result = TwelveData(Gateway(db, client)).get_intraday_prices("AAPL", "NASDAQ", "USD", "1h")

    assert [row["close"] for row in result.data] == ["102", "103"]
    assert result.data[0]["time"] < result.data[1]["time"]
    assert all("TEST_TWELVE_ONLY" not in row.key for row in db.scalars(select(ApiCache)))


def test_sec_company_search_returns_importable_cik(db, monkeypatch):
    monkeypatch.setattr(settings, "sec_user_agent", "StockEasy Tests tests@example.com")
    payload = {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [
            [320193, "Apple Inc.", "AAPL", "Nasdaq"],
            [789019, "Microsoft Corp", "MSFT", "Nasdaq"],
        ],
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )

    result = SEC(Gateway(db, client)).search_companies("apple")

    assert result.data == [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "asset_type": "STOCK",
            "exchange": "NASDAQ",
            "currency": "USD",
            "provider": "sec",
            "provider_asset_id": "0000320193",
            "cik": "0000320193",
        }
    ]


def test_assets_watchlists_and_private_manual_prices(auth, db):
    data = {"symbol": "test", "name": "Test fund", "currency": "EUR", "asset_type": "MUTUAL_FUND"}
    asset = auth.post("/api/assets", json=data).json()
    assert asset["symbol"] == "TEST"
    assert auth.post("/api/assets", json=data).json()["id"] == asset["id"]
    assert auth.post("/api/assets", json={**data, "currency": "ZZZ"}).status_code == 422
    assert (
        auth.post(
            f"/api/assets/{asset['id']}/prices",
            json={"date": "2025-01-02", "close": "123.123456789123"},
        ).status_code
        == 200
    )
    rows = auth.get(f"/api/assets/{asset['id']}/prices").json()
    assert Decimal(rows["items"][0]["close"]) == Decimal("123.123456789123")
    w = auth.post("/api/watchlists", json={"name": "My list"}).json()
    assert (
        auth.post(f"/api/watchlists/{w['id']}/items", json={"asset_id": asset["id"]}).status_code
        == 200
    )
    assert len(auth.get(f"/api/watchlists/{w['id']}/items").json()) == 1
    r = auth.post(
        "/api/auth/login", json={"username": "bob", "password": "another secure password"}
    )
    auth.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert auth.get(f"/api/assets/{asset['id']}").status_code == 404
    assert auth.get(f"/api/watchlists/{w['id']}/items").status_code == 404


def test_import_sec_company_preserves_cik(auth):
    response = auth.post(
        "/api/assets",
        json={
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "currency": "USD",
            "asset_type": "STOCK",
            "exchange": "NASDAQ",
            "provider": "sec",
            "provider_asset_id": "0000320193",
            "cik": "0000320193",
        },
    )

    assert response.status_code == 200
    assert response.json()["cik"] == "0000320193"
    asset_id = response.json()["id"]
    assert auth.get(f"/api/assets/{asset_id}").status_code == 200


def test_import_sec_company_also_links_fmp_for_market_prices(auth, db):
    response = auth.post(
        "/api/assets",
        json={
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "currency": "USD",
            "asset_type": "STOCK",
            "exchange": "NASDAQ",
            "provider": "sec",
            "provider_asset_id": "0000320193",
            "cik": "0000320193",
        },
    )

    mappings = {
        row.provider: row
        for row in db.scalars(
            select(ProviderMapping).where(ProviderMapping.asset_id == response.json()["id"])
        )
    }
    assert mappings["sec"].provider_asset_id == "0000320193"
    assert mappings["fmp"].provider_symbol == "AAPL"


def test_import_eodhd_fund_preserves_full_provider_symbol(auth, db):
    response = auth.post(
        "/api/assets",
        json={
            "symbol": "IE00BDD48S37",
            "name": "Vanguard EUR Corporate 1-3 Year",
            "currency": "EUR",
            "asset_type": "MUTUAL_FUND",
            "exchange": "EUFUND",
            "provider": "eodhd",
            "provider_asset_id": "IE00BDD48S37.EUFUND",
        },
    )

    mapping = db.get(ProviderMapping, (response.json()["id"], "eodhd"))
    assert mapping.provider_symbol == "IE00BDD48S37"
    assert mapping.provider_asset_id == "IE00BDD48S37.EUFUND"
