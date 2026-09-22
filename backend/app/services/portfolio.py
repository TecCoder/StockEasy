import threading
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.returns import xirr
from app.models import Asset, AssetPrice
from app.models.portfolio import Portfolio, Transaction
from app.portfolio.engine import Entry, reconstruct
from app.schemas.portfolio import TransactionInput
from app.services.fx import FXService
from app.services.market import MarketService, own_asset

LEDGER_LOCK = threading.RLock()


def own_portfolio(db: Session, user_id: str, portfolio_id: str) -> Portfolio:
    p = db.scalar(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    if not p:
        raise HTTPException(404, "Cartera no encontrada")
    return p


def entries(db: Session, portfolio_id: str, on: date | None = None) -> list[Transaction]:
    query = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    if on:
        query = query.where(Transaction.date <= on)
    return list(
        db.scalars(query.order_by(Transaction.date, Transaction.created_at, Transaction.id))
    )


def transaction_dict(t: Transaction) -> dict[str, Any]:
    return {
        k: getattr(t, k)
        for k in (
            "id",
            "asset_id",
            "date",
            "executed_at",
            "transaction_type",
            "quantity",
            "price",
            "currency",
            "fees",
            "taxes",
            "fx_rate",
            "input_currency",
            "input_price",
            "input_fees",
            "input_taxes",
            "input_to_asset_rate",
            "conversion_provider",
            "conversion_effective_at",
            "conversion_precision",
            "broker",
            "notes",
            "external_id",
        )
    }


def save_transaction(
    db: Session,
    portfolio: Portfolio,
    body: TransactionInput,
    transaction_id: str | None = None,
    commit: bool = True,
) -> Transaction:
    original_currency = body.currency
    original_price = body.price
    original_fees = body.fees
    original_taxes = body.taxes
    executed_at = body.executed_at or datetime.combine(body.date, time(12), tzinfo=UTC)
    conversion = None
    if body.asset_id:
        asset = own_asset(db, portfolio.user_id, body.asset_id)
        conversion = FXService(db).get_at(
            portfolio.user_id,
            original_currency,
            asset.currency,
            executed_at,
            body.input_to_asset_rate,
        )
        if conversion is None:
            raise HTTPException(
                422,
                f"No hay tipo de cambio {original_currency}/{asset.currency} para la ejecución",
            )
        quant = Decimal("0.000000000001")
        body = body.model_copy(
            update={
                "price": (body.price * conversion.rate).quantize(quant, ROUND_HALF_UP),
                "fees": (body.fees * conversion.rate).quantize(quant, ROUND_HALF_UP),
                "taxes": (body.taxes * conversion.rate).quantize(quant, ROUND_HALF_UP),
                "currency": asset.currency,
                "input_to_asset_rate": conversion.rate,
            }
        )
    fx = Decimal(1) if body.currency == portfolio.base_currency else body.fx_rate
    if body.currency == portfolio.base_currency and body.fx_rate not in {None, Decimal(1)}:
        raise HTTPException(422, "Misma moneda requiere FX=1")
    if fx is None:
        if conversion and original_currency == portfolio.base_currency:
            fx = Decimal(1) / conversion.rate
        else:
            portfolio_conversion = FXService(db).get_at(
                portfolio.user_id,
                body.currency,
                portfolio.base_currency,
                executed_at,
            )
            fx = portfolio_conversion.rate if portfolio_conversion else None
    if fx is None:
        raise HTTPException(
            422,
            "Falta FX histórico. Introduce el tipo de cambio a moneda base o regístralo en Divisas.",
        )
    with LEDGER_LOCK:
        row = db.get(Transaction, transaction_id) if transaction_id else None
        if transaction_id and (row is None or row.portfolio_id != portfolio.id):
            raise HTTPException(404, "Transacción no encontrada")
        values = {
            **body.model_dump(),
            "executed_at": body.executed_at,
            "fx_rate": fx,
            "input_currency": original_currency,
            "input_price": original_price,
            "input_fees": original_fees,
            "input_taxes": original_taxes,
            "input_to_asset_rate": conversion.rate if conversion else Decimal(1),
            "conversion_provider": conversion.provider if conversion else "identity",
            "conversion_effective_at": conversion.effective_at if conversion else executed_at,
            "conversion_precision": conversion.precision if conversion else "exact",
        }
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            row = Transaction(portfolio_id=portfolio.id, **values)
            db.add(row)
        try:
            db.flush()
            ordered: list[Entry] = list(entries(db, portfolio.id))
            reconstruct(ordered)
            if commit:
                db.commit()
        except (ValueError, IntegrityError) as exc:
            db.rollback()
            raise HTTPException(
                422, str(exc) if isinstance(exc, ValueError) else "ID de transacción duplicado"
            ) from None
        return row


def remove_transaction(db: Session, portfolio: Portfolio, transaction_id: str) -> None:
    with LEDGER_LOCK:
        row = db.get(Transaction, transaction_id)
        if not row or row.portfolio_id != portfolio.id:
            raise HTTPException(404, "Transacción no encontrada")
        db.delete(row)
        db.flush()
        try:
            reconstruct(list(entries(db, portfolio.id)))
            db.commit()
        except ValueError as exc:
            db.rollback()
            raise HTTPException(422, f"No se puede eliminar: {exc}") from None


def snapshot(
    db: Session,
    portfolio: Portfolio,
    on: date | None = None,
    live: bool = True,
    display_currency: str | None = None,
) -> dict[str, Any]:
    day = on or date.today()
    target_currency = display_currency or portfolio.base_currency
    tx = entries(db, portfolio.id, day)
    ledger = reconstruct(list(tx))
    fx_service = FXService(db)
    base_to_target = fx_service.get(
        portfolio.user_id,
        portfolio.base_currency,
        target_currency,
        day,
        fetch=live,
    )
    positions: list[dict[str, Any]] = []
    missing = []
    valuation_warnings = []
    if base_to_target is None:
        missing.append(f"Falta FX {portfolio.base_currency}/{target_currency}")
    security_value = Decimal(0)
    cash_value = Decimal(0)
    cost_basis_base = sum((p.cost_base for p in ledger.positions.values()), Decimal(0))
    cost_basis = cost_basis_base * base_to_target if base_to_target is not None else Decimal(0)
    for p in ledger.positions.values():
        asset = db.get(Asset, p.asset_id)
        assert asset is not None
        price = None
        price_date = None
        price_provider = None
        if p.quantity:
            if live:
                quote = MarketService(db).quote(asset)
                price = Decimal(quote["price"]) if quote["price"] is not None else None
                price_date = str(quote.get("date") or "")
                price_provider = quote.get("provider")
            else:
                row = db.scalar(
                    select(AssetPrice)
                    .where(
                        AssetPrice.asset_id == asset.id,
                        AssetPrice.date <= day,
                        AssetPrice.date >= day - timedelta(days=7),
                    )
                    .order_by(AssetPrice.date.desc(), AssetPrice.retrieved_at.desc())
                )
                if row:
                    price, price_date, price_provider = (
                        row.close,
                        row.date.isoformat(),
                        row.provider,
                    )
        fx = fx_service.get(
            portfolio.user_id,
            asset.currency,
            target_currency,
            day,
            fetch=live,
        )
        position_cost = p.cost_base * base_to_target if base_to_target is not None else None
        value = (
            p.quantity * price * fx
            if price is not None and fx is not None
            else Decimal(0)
            if p.quantity == 0
            else None
        )
        valuation_method = "market"
        if value is None and position_cost is not None:
            value = position_cost
            valuation_method = "cost_basis_fallback"
            valuation_warnings.append(
                f"{asset.symbol}: valor estimado usando el coste aportado por falta de cotización"
            )
        elif value is None:
            missing.append(
                f"{asset.symbol}: falta precio o FX {asset.currency}/{target_currency}"
            )
        if value is not None:
            security_value += value
        realized = p.realized_base * base_to_target if base_to_target is not None else None
        dividends = p.dividends_base * base_to_target if base_to_target is not None else None
        unrealized = value - position_cost if value is not None and position_cost is not None else None
        positions.append(
            {
                "asset_id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "sector": asset.sector,
                "country": asset.country,
                "quantity": p.quantity,
                "currency": asset.currency,
                "average_cost": p.cost / p.quantity if p.quantity else None,
                "current_price": price,
                "price_date": price_date,
                "price_provider": price_provider,
                "valuation_method": valuation_method,
                "cost_basis": position_cost,
                "current_value": value,
                "unrealized_pl": unrealized,
                "unrealized_percent": unrealized / p.cost_base * 100
                if unrealized is not None and p.cost_base > 0
                else None,
                "realized_pl": realized,
                "dividends": dividends,
                "total_return": unrealized + realized + dividends
                if unrealized is not None and realized is not None and dividends is not None
                else None,
            }
        )
    positions_complete = not missing
    positions_value = security_value if positions_complete else None
    positions_pnl = (
        sum(
            (
                position["total_return"]
                for position in positions
                if position["total_return"] is not None
            ),
            Decimal(0),
        )
        if positions_complete
        else None
    )
    for currency, amount in ledger.cash.items():
        fx = fx_service.get(portfolio.user_id, currency, target_currency, day, fetch=live)
        if amount and fx is None:
            missing.append(f"Efectivo: falta FX {currency}/{target_currency}")
        elif fx:
            cash_value += amount * fx
    complete = not missing
    total = security_value + cash_value if complete else None
    has_negative_cash = any(v < 0 for v in ledger.cash.values())
    performance_ok = complete and not ledger.transfer_valuation_missing and not has_negative_cash
    contributions = (
        ledger.contributions * base_to_target if base_to_target is not None else None
    )
    profit = (
        total - contributions
        if performance_ok and total is not None and contributions is not None
        else None
    )
    for position in positions:
        position["weight"] = (
            position["current_value"] / security_value * 100
            if security_value > 0 and position["current_value"] is not None
            else None
        )
    annualized = (
        xirr(
            [
                *ledger.external_flows,
                (day, total / base_to_target),
            ]
        )
        if performance_ok and total is not None and base_to_target is not None
        else None
    )
    dividends_ytd = sum(
        (
            (t.quantity * t.price - t.fees - t.taxes) * t.fx_rate
            for t in tx
            if t.transaction_type == "DIVIDEND" and t.date.year == day.year
        ),
        Decimal(0),
    ) * (base_to_target or Decimal(0))
    return {
        "date": day,
        "base_currency": target_currency,
        "portfolio_currency": portfolio.base_currency,
        "positions": positions,
        "cash_balances": ledger.cash,
        "cash": cash_value if not any(m.startswith("Efectivo") for m in missing) else None,
        "total_value": total,
        "positions_value": positions_value,
        "positions_pnl": positions_pnl,
        "positions_return_percent": positions_pnl / cost_basis * 100
        if positions_pnl is not None and cost_basis > 0
        else None,
        "cost_basis": cost_basis,
        "total_pl": profit,
        "return_percent": profit / ledger.contributions * 100
        if profit is not None and ledger.contributions > 0
        else None,
        "realized_pl": sum((p.realized_base for p in ledger.positions.values()), Decimal(0)),
        "dividends": sum((p.dividends_base for p in ledger.positions.values()), Decimal(0)),
        "dividends_ytd": dividends_ytd,
        "net_contributions": contributions,
        "xirr": annualized,
        "twr": None,
        "complete": complete,
        "missing": missing,
        "warnings": (
            [
                "Aportaciones de efectivo no registradas: rentabilidad basada en flujos no disponible"
            ]
            if has_negative_cash
            else []
        )
        + (
            ["Transferencias sin valor de mercado de entrada/salida: rentabilidad no disponible"]
            if ledger.transfer_valuation_missing
            else []
        )
        + valuation_warnings
        + ["TWR no disponible sin valoraciones verificadas en cada frontera de flujo"],
    }


def chart_history(
    db: Session,
    portfolio: Portfolio,
    asset_ids: list[str] | None = None,
    days: int = 365,
    display_currency: str | None = None,
) -> dict[str, Any]:
    """Daily position value, carrying cost and total P/L without price lookahead."""
    all_transactions = entries(db, portfolio.id)
    position_asset_ids = {transaction.asset_id for transaction in all_transactions if transaction.asset_id}
    selected_ids = set(asset_ids or position_asset_ids)
    if asset_ids and not selected_ids.issubset(position_asset_ids):
        raise HTTPException(422, "Algún activo no pertenece a esta cartera")
    selected_transactions = [
        transaction for transaction in all_transactions if transaction.asset_id in selected_ids
    ]
    if not selected_transactions:
        return {
            "base_currency": display_currency or portfolio.base_currency,
            "portfolio_currency": portfolio.base_currency,
            "selection": [],
            "items": [],
            "missing_days": 0,
        }

    assets = {
        asset.id: asset
        for asset in db.scalars(
            select(Asset).where(Asset.user_id == portfolio.user_id, Asset.id.in_(selected_ids))
        )
    }
    target_currency = display_currency or portfolio.base_currency
    end = date.today()
    start = max(selected_transactions[0].date, end - timedelta(days=days - 1))
    fx_service = FXService(db)
    for source_currency in {portfolio.base_currency, *(asset.currency for asset in assets.values())}:
        fx_service.ensure_history(
            portfolio.user_id,
            source_currency,
            target_currency,
            start - timedelta(days=7),
            end,
        )
    prices: dict[str, list[AssetPrice]] = {asset_id: [] for asset_id in selected_ids}
    for price in db.scalars(
        select(AssetPrice)
        .where(
            AssetPrice.asset_id.in_(selected_ids),
            AssetPrice.date >= start - timedelta(days=7),
            AssetPrice.date <= end,
        )
        .order_by(AssetPrice.asset_id, AssetPrice.date, AssetPrice.retrieved_at)
    ):
        prices[price.asset_id].append(price)

    price_indexes = {asset_id: 0 for asset_id in selected_ids}
    latest_prices: dict[str, AssetPrice] = {}
    fx_cache: dict[tuple[str, date], Decimal | None] = {}
    items: list[dict[str, Any]] = []
    missing_days = 0
    day = start
    while day <= end:
        for asset_id, rows in prices.items():
            index = price_indexes[asset_id]
            while index < len(rows) and rows[index].date <= day:
                latest_prices[asset_id] = rows[index]
                index += 1
            price_indexes[asset_id] = index

        ledger = reconstruct([transaction for transaction in selected_transactions if transaction.date <= day])
        base_fx = fx_service.get(
            portfolio.user_id,
            portfolio.base_currency,
            target_currency,
            day,
            fetch=False,
        )
        invested_base = sum(
            (position.cost_base for position in ledger.positions.values()), Decimal(0)
        )
        realized_base = sum(
            (position.realized_base for position in ledger.positions.values()), Decimal(0)
        )
        dividends_base = sum(
            (position.dividends_base for position in ledger.positions.values()), Decimal(0)
        )
        invested = invested_base * base_fx if base_fx is not None else None
        realized = realized_base * base_fx if base_fx is not None else None
        dividends = dividends_base * base_fx if base_fx is not None else None
        value = Decimal(0)
        missing: list[str] = []
        if base_fx is None:
            missing.append(f"Falta FX {portfolio.base_currency}/{target_currency}")
        for position in ledger.positions.values():
            if position.quantity == 0:
                continue
            asset = assets[position.asset_id]
            latest_price = latest_prices.get(position.asset_id)
            if latest_price is None or latest_price.date < day - timedelta(days=7):
                missing.append(f"{asset.symbol}: falta precio")
                continue
            fx_key = (asset.currency, day)
            if fx_key not in fx_cache:
                fx_cache[fx_key] = fx_service.get(
                    portfolio.user_id,
                    asset.currency,
                    target_currency,
                    day,
                    fetch=False,
                )
            fx = fx_cache[fx_key]
            if fx is None:
                missing.append(
                    f"{asset.symbol}: falta FX {asset.currency}/{target_currency}"
                )
                continue
            value += position.quantity * latest_price.close * fx

        complete = not missing
        if not complete:
            missing_days += 1
        items.append(
            {
                "date": day,
                "invested": invested,
                "value": value if complete else None,
                "pnl": value - invested + realized + dividends
                if complete
                and invested is not None
                and realized is not None
                and dividends is not None
                else None,
                "realized": realized,
                "dividends": dividends,
                "complete": complete,
                "missing": missing,
            }
        )
        day += timedelta(days=1)

    return {
        "base_currency": target_currency,
        "portfolio_currency": portfolio.base_currency,
        "selection": [
            {"asset_id": asset.id, "symbol": asset.symbol, "name": asset.name}
            for asset in sorted(assets.values(), key=lambda item: item.symbol)
        ],
        "items": items,
        "missing_days": missing_days,
        "method": (
            "Coste vivo ponderado frente a valor histórico; P/L = valor - coste vivo + "
            "P/L realizado + dividendos. Último cierre/FX conocido hasta 7 días, nunca futuro."
        ),
    }
