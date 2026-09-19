from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app.db.base import utcnow
from app.models import ApiCache, ProviderUsage
from app.providers.base import ProviderError
from app.providers.gateway import Gateway


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
