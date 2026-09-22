from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from app.analytics.returns import twr, xirr
from app.models.portfolio import FXRate
from app.portfolio.engine import reconstruct
from app.services.fx import FXService


def entry(kind, quantity=1, price=0, fees=0, taxes=0, asset="a", currency="EUR", fx="1"):
    return SimpleNamespace(
        transaction_type=kind,
        quantity=D(str(quantity)),
        price=D(str(price)),
        fees=D(str(fees)),
        taxes=D(str(taxes)),
        asset_id=asset,
        currency=currency,
        fx_rate=D(fx),
        date=date(2024, 1, 1),
    )


def test_weighted_average_realized_dividends_and_split():
    ledger = reconstruct(
        [
            entry("DEPOSIT", price=5000, asset=None),
            entry("BUY", 10, 100, 10),
            entry("BUY", 10, 200),
            entry("SELL", 5, 250, 5),
            entry("DIVIDEND", price=30, taxes=6),
            entry("SPLIT", 2),
        ]
    )
    p = ledger.positions["a"]
    assert p.quantity == 30
    assert p.cost == D("2257.5")
    assert p.cost / p.quantity == D("75.25")
    assert p.realized == D("492.5")
    assert p.dividends == 24
    assert ledger.cash["EUR"] == 3259
    with pytest.raises(ValueError):
        reconstruct([entry("BUY", 1, 10), entry("SELL", 2, 10)])


def test_xirr_twr_and_invalid_flows():
    assert xirr([(date(2023, 1, 1), D(-1000)), (date(2024, 1, 1), D(1100))]) == pytest.approx(0.1)
    assert xirr([(date(2023, 1, 1), D(100))]) is None
    assert (
        xirr([(date(2023, 1, 1), D(-100)), (date(2024, 1, 1), D(200)), (date(2025, 1, 1), D(-50))])
        is None
    )
    assert twr([(D(100), D(160), D(50)), (D(160), D(176), D(0))]) == D(".21")


def test_fx_no_parity_and_no_lookahead(db):
    from sqlalchemy import select

    from app.models import User

    user = db.scalar(select(User).where(User.username == "alice"))
    service = FXService(db)
    assert service.get(user.id, "EUR", "EUR", date(2024, 1, 1)) == 1
    assert service.get(user.id, "USD", "EUR", date(2024, 1, 1)) is None
    db.add(
        FXRate(
            user_id=user.id,
            base="USD",
            quote="EUR",
            date=date(2024, 1, 2),
            rate=D(".9"),
            provider="manual",
        )
    )
    db.commit()
    assert service.get(user.id, "USD", "EUR", date(2024, 1, 1)) is None
    assert service.get(user.id, "USD", "EUR", date(2024, 1, 3)) == D(".9")
    assert service.get(user.id, "EUR", "USD", date(2024, 1, 3)) == D(1) / D(".9")


def test_portfolio_api_edit_delete_validation_and_ownership(auth):
    asset = auth.post(
        "/api/assets",
        json={"symbol": "FUND", "name": "Fund", "currency": "EUR", "asset_type": "MUTUAL_FUND"},
    ).json()
    p = auth.post("/api/portfolios", json={"name": "Core"}).json()
    path = f"/api/portfolios/{p['id']}"
    base = {
        "date": "2024-01-01",
        "currency": "EUR",
        "price": "100",
        "quantity": "10",
        "asset_id": asset["id"],
        "transaction_type": "BUY",
    }
    auth.post(
        path + "/transactions",
        json={
            "date": "2024-01-01",
            "transaction_type": "DEPOSIT",
            "currency": "EUR",
            "price": "2000",
        },
    )
    buy = auth.post(path + "/transactions", json=base)
    assert buy.status_code == 200
    assert (
        auth.post(
            path + "/transactions", json={**base, "transaction_type": "SELL", "quantity": "20"}
        ).status_code
        == 422
    )
    sell = auth.post(
        path + "/transactions",
        json={
            **base,
            "date": "2024-01-02",
            "transaction_type": "SELL",
            "quantity": "5",
            "price": "150",
        },
    )
    assert sell.status_code == 200
    assert auth.delete(path + "/transactions/" + buy.json()["id"]).status_code == 422
    assert (
        auth.put(
            path + "/transactions/" + buy.json()["id"], json={**base, "quantity": "2"}
        ).status_code
        == 422
    )
    today = date.today().isoformat()
    auth.post(f"/api/assets/{asset['id']}/prices", json={"date": today, "close": "160"})
    snap = auth.get(path + "/positions").json()
    assert D(str(snap["total_value"])) == 2550
    assert D(str(snap["total_pl"])) == 550
    assert D(str(snap["positions"][0]["unrealized_pl"])) == 300
    assert D(str(snap["realized_pl"])) == 250
    assert "transaction_type" in auth.get(path + "/export").text
    r = auth.post(
        "/api/auth/login", json={"username": "bob", "password": "another secure password"}
    )
    auth.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert auth.get(path + "/transactions").status_code == 404
    assert auth.get(path + "/export").status_code == 404


def test_csv_preview_does_not_write_and_import_rolls_back(auth):
    p = auth.post("/api/portfolios", json={"name": "Import"}).json()
    path = f"/api/portfolios/{p['id']}"
    content = (
        "date,ticker,transaction_type,quantity,price,currency\n2024-01-01,,DEPOSIT,1,1000,EUR\n"
    )
    preview = auth.post(path + "/import", json={"content": content}).json()
    assert preview["valid"] and not auth.get(path + "/transactions").json()
    assert (
        auth.post(path + "/import", json={"content": content, "confirm": True}).json()["imported"]
        == 1
    )
    assert (
        auth.post(path + "/import", json={"content": content, "confirm": True}).status_code == 422
    )
    assert len(auth.get(path + "/transactions").json()) == 1


def test_myinvestor_csv_imports_finalized_orders_and_skips_rejected(auth):
    asset = auth.post(
        "/api/assets",
        json={
            "symbol": "IE000QAZP7L2",
            "name": "iShares Emerging Markets Index Fund (IE) S Acc EUR",
            "currency": "EUR",
            "asset_type": "MUTUAL_FUND",
            "exchange": "EUFUND",
        },
    ).json()
    portfolio = auth.post("/api/portfolios", json={"name": "MyInvestor"}).json()
    path = f"/api/portfolios/{portfolio['id']}"
    content = (
        "Fecha de la orden;ISIN;Importe estimado;N\u00ba de participaciones;Estado\n"
        "02/01/2024;IE000QAZP7L2;1.234,56 EUR;100,5;Finalizada\n"
        "03/01/2024;IE000QAZP7L2;100,00 EUR;;Rechazada\n"
    )
    body = {"content": content, "filename": "ordenes.csv"}
    preview = auth.post(path + "/import", json=body).json()
    assert preview["valid"], preview
    assert preview["rows"][1]["skipped"]
    result = auth.post(path + "/import", json={**body, "confirm": True}).json()
    assert result["imported"] == 1
    transactions = auth.get(path + "/transactions").json()
    assert len(transactions) == 1
    assert transactions[0]["asset_id"] == asset["id"]
    assert transactions[0]["transaction_type"] == "BUY"
    assert D(transactions[0]["quantity"]) == D("100.5")
    assert transactions[0]["broker"] == "MyInvestor"


def test_portfolio_charts_reconstruct_daily_value_cost_and_pnl(auth):
    asset = auth.post(
        "/api/assets",
        json={"symbol": "FUND", "name": "Fund", "currency": "EUR", "asset_type": "MUTUAL_FUND"},
    ).json()
    portfolio = auth.post("/api/portfolios", json={"name": "Charts"}).json()
    path = f"/api/portfolios/{portfolio['id']}"
    buy_day = date.today() - timedelta(days=2)
    sell_day = date.today() - timedelta(days=1)
    base = {"asset_id": asset["id"], "currency": "EUR"}
    assert auth.post(
        path + "/transactions",
        json={**base, "date": buy_day.isoformat(), "transaction_type": "BUY", "quantity": "2", "price": "100"},
    ).status_code == 200
    assert auth.post(
        path + "/transactions",
        json={**base, "date": sell_day.isoformat(), "transaction_type": "SELL", "quantity": "1", "price": "130"},
    ).status_code == 200
    auth.post(f"/api/assets/{asset['id']}/prices", json={"date": buy_day.isoformat(), "close": "110"})
    auth.post(f"/api/assets/{asset['id']}/prices", json={"date": sell_day.isoformat(), "close": "120"})

    response = auth.get(path + f"/charts?days=5&asset_ids={asset['id']}")
    assert response.status_code == 200
    data = response.json()
    points = {point["date"]: point for point in data["items"]}
    assert D(points[buy_day.isoformat()]["invested"]) == 200
    assert D(points[buy_day.isoformat()]["value"]) == 220
    assert D(points[buy_day.isoformat()]["pnl"]) == 20
    assert D(points[sell_day.isoformat()]["invested"]) == 100
    assert D(points[sell_day.isoformat()]["value"]) == 120
    assert D(points[sell_day.isoformat()]["pnl"]) == 50
    assert data["selection"][0]["symbol"] == "FUND"
    assert auth.get(path + "/charts?asset_ids=not-owned").status_code == 422


def test_transaction_converts_input_currency_and_portfolio_displays_usd(auth):
    asset = auth.post(
        "/api/assets",
        json={"symbol": "USD-FUND", "name": "USD Fund", "currency": "USD", "asset_type": "ETF"},
    ).json()
    portfolio = auth.post("/api/portfolios", json={"name": "Multi currency"}).json()
    path = f"/api/portfolios/{portfolio['id']}"
    executed = datetime.now(UTC) - timedelta(minutes=1)
    response = auth.post(
        path + "/transactions",
        json={
            "asset_id": asset["id"],
            "date": executed.date().isoformat(),
            "executed_at": executed.isoformat(),
            "transaction_type": "BUY",
            "quantity": "1",
            "price": "50",
            "currency": "EUR",
            "input_to_asset_rate": "2",
        },
    )
    assert response.status_code == 200, response.text
    transaction = response.json()
    assert transaction["currency"] == "USD"
    assert transaction["input_currency"] == "EUR"
    assert D(transaction["input_price"]) == 50
    assert D(transaction["price"]) == 100
    assert D(transaction["input_to_asset_rate"]) == 2
    assert transaction["conversion_provider"] == "manual"

    today = date.today().isoformat()
    auth.post(f"/api/assets/{asset['id']}/prices", json={"date": today, "close": "110"})
    auth.post("/api/fx", json={"base": "USD", "quote": "EUR", "date": today, "rate": ".5"})
    eur = auth.get(path + "/positions?display_currency=EUR").json()
    usd = auth.get(path + "/positions?display_currency=USD").json()
    assert D(eur["positions_value"]) == 55
    assert D(eur["cost_basis"]) == 50
    assert D(usd["positions_value"]) == 110
    assert D(usd["cost_basis"]) == 100
    assert D(usd["positions_pnl"]) == 10


def test_positions_use_cost_basis_when_market_price_is_unavailable(auth):
    asset = auth.post(
        "/api/assets",
        json={"symbol": "NO-QUOTE", "name": "No quote", "currency": "EUR"},
    ).json()
    portfolio = auth.post("/api/portfolios", json={"name": "Fallback valuation"}).json()
    path = f"/api/portfolios/{portfolio['id']}"
    today = date.today().isoformat()
    assert auth.post(
        path + "/transactions",
        json={
            "date": today,
            "transaction_type": "DEPOSIT",
            "currency": "EUR",
            "price": "1000",
        },
    ).status_code == 200
    assert auth.post(
        path + "/transactions",
        json={
            "asset_id": asset["id"],
            "date": today,
            "transaction_type": "BUY",
            "quantity": "2",
            "price": "100",
            "currency": "EUR",
        },
    ).status_code == 200

    snapshot = auth.get(path + "/positions").json()
    position = snapshot["positions"][0]
    assert D(snapshot["positions_value"]) == 200
    assert D(position["current_value"]) == 200
    assert D(position["unrealized_pl"]) == 0
    assert position["valuation_method"] == "cost_basis_fallback"
    assert snapshot["complete"] is True
    assert any("coste aportado" in warning for warning in snapshot["warnings"])
