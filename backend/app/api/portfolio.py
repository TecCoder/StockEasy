import csv
import hashlib
import io
import json
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.auth.security import DB, CurrentUser
from app.models import Asset
from app.models.portfolio import FXRate, Portfolio
from app.schemas.portfolio import FXInput, PortfolioCreate, TransactionInput
from app.services.fx import FXService
from app.services.portfolio import (
    entries,
    own_portfolio,
    remove_transaction,
    save_transaction,
    snapshot,
    transaction_dict,
)

router = APIRouter(tags=["Portfolio"])


@router.get("/portfolios")
def portfolios(user: CurrentUser, db: DB) -> list[dict[str, Any]]:
    return [
        {"id": p.id, "name": p.name, "description": p.description, "base_currency": p.base_currency}
        for p in db.scalars(select(Portfolio).where(Portfolio.user_id == user.id))
    ]


@router.post("/portfolios")
def create_portfolio(body: PortfolioCreate, user: CurrentUser, db: DB) -> dict[str, Any]:
    p = Portfolio(user_id=user.id, **body.model_dump())
    db.add(p)
    db.commit()
    return {"id": p.id, "name": p.name, "base_currency": p.base_currency}


@router.get("/portfolios/{portfolio_id}/transactions")
def transactions(portfolio_id: str, user: CurrentUser, db: DB) -> list[dict[str, Any]]:
    own_portfolio(db, user.id, portfolio_id)
    return [transaction_dict(t) for t in entries(db, portfolio_id)]


@router.post("/portfolios/{portfolio_id}/transactions")
def create_transaction(
    portfolio_id: str, body: TransactionInput, user: CurrentUser, db: DB
) -> dict[str, Any]:
    return transaction_dict(save_transaction(db, own_portfolio(db, user.id, portfolio_id), body))


@router.put("/portfolios/{portfolio_id}/transactions/{transaction_id}")
def edit_transaction(
    portfolio_id: str, transaction_id: str, body: TransactionInput, user: CurrentUser, db: DB
) -> dict[str, Any]:
    return transaction_dict(
        save_transaction(db, own_portfolio(db, user.id, portfolio_id), body, transaction_id)
    )


@router.delete("/portfolios/{portfolio_id}/transactions/{transaction_id}")
def delete_transaction(
    portfolio_id: str, transaction_id: str, user: CurrentUser, db: DB
) -> dict[str, bool]:
    remove_transaction(db, own_portfolio(db, user.id, portfolio_id), transaction_id)
    return {"ok": True}


@router.get("/portfolios/{portfolio_id}/positions")
def positions(portfolio_id: str, user: CurrentUser, db: DB) -> dict[str, Any]:
    return snapshot(db, own_portfolio(db, user.id, portfolio_id))


@router.get("/portfolios/{portfolio_id}/performance")
def performance(portfolio_id: str, user: CurrentUser, db: DB) -> dict[str, Any]:
    p = own_portfolio(db, user.id, portfolio_id)
    return snapshot(db, p)


@router.get("/portfolios/{portfolio_id}/history")
def history(portfolio_id: str, user: CurrentUser, db: DB, days: int = 365) -> dict[str, Any]:
    p = own_portfolio(db, user.id, portfolio_id)
    if not 1 <= days <= 3653:
        raise HTTPException(422, "Rango de 1 a 3653 días")
    tx = entries(db, p.id)
    if not tx:
        return {"items": []}
    start = max(tx[0].date, date.today() - timedelta(days=days))
    items = []
    day = start
    while day <= date.today():
        s = snapshot(db, p, day, live=False)
        items.append(
            {
                "date": day,
                "value": s["total_value"],
                "complete": s["complete"],
                "missing": s["missing"],
            }
        )
        day += timedelta(days=1)
    return {
        "items": items,
        "method": "ledger + last known close/FX within 7 days; never future data",
    }


@router.post("/fx")
def save_fx(body: FXInput, user: CurrentUser, db: DB) -> dict[str, bool]:
    db.merge(FXRate(user_id=user.id, provider="manual", **body.model_dump()))
    db.commit()
    return {"ok": True}


@router.get("/fx")
def get_fx(user: CurrentUser, db: DB, base: str, quote: str, on: date) -> dict[str, Any]:
    from app.schemas.market import currency

    try:
        base, quote = currency(base), currency(quote)
    except ValueError:
        raise HTTPException(422, "Moneda inválida") from None
    if on > date.today():
        raise HTTPException(422, "Fecha futura")
    value = FXService(db).get(user.id, base, quote, on, fetch=True)
    return {"base": base, "quote": quote, "date": on, "rate": value}


def csv_safe(value: Any) -> str:
    value = str(value) if value is not None else ""
    return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value


@router.get("/portfolios/{portfolio_id}/export")
def export_portfolio(portfolio_id: str, user: CurrentUser, db: DB, format: str = "csv") -> Response:
    p = own_portfolio(db, user.id, portfolio_id)
    rows = []
    for t in entries(db, p.id):
        asset = db.get(Asset, t.asset_id) if t.asset_id else None
        row = transaction_dict(t)
        row.update(
            {
                "ticker": asset.symbol if asset else "",
                "asset_type": asset.asset_type if asset else "",
                "exchange": asset.exchange if asset else "",
            }
        )
        rows.append(row)
    if format == "json":
        content = json.dumps(
            jsonable_encoder(
                {
                    "portfolio": {"name": p.name, "base_currency": p.base_currency},
                    "transactions": rows,
                }
            ),
            ensure_ascii=False,
            indent=2,
        )
        return Response(
            content,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="portfolio.json"'},
        )
    out = io.StringIO(newline="")
    columns = [
        "date",
        "ticker",
        "asset_type",
        "exchange",
        "transaction_type",
        "quantity",
        "price",
        "currency",
        "fees",
        "taxes",
        "fx_rate",
        "broker",
        "notes",
        "external_id",
    ]
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    writer.writerows({k: csv_safe(r[k]) for k in columns} for r in rows)
    return Response(
        out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


class CSVImport(BaseModel):
    content: str = Field(max_length=1_000_000)
    confirm: bool = False


@router.post("/portfolios/{portfolio_id}/import")
def import_csv(portfolio_id: str, body: CSVImport, user: CurrentUser, db: DB) -> dict[str, Any]:
    p = own_portfolio(db, user.id, portfolio_id)
    parsed: list[TransactionInput] = []
    preview = []
    for i, row in enumerate(csv.DictReader(io.StringIO(body.content.lstrip("\ufeff"))), start=2):
        if i > 1002:
            raise HTTPException(422, "Máximo 1000 filas por importación")
        try:
            symbol = row.get("ticker", "").strip().upper()
            candidates = (
                list(
                    db.scalars(
                        select(Asset).where(Asset.user_id == user.id, Asset.symbol == symbol)
                    )
                )
                if symbol
                else []
            )
            if row.get("exchange"):
                candidates = [a for a in candidates if a.exchange == row["exchange"]]
            if row.get("asset_type"):
                candidates = [a for a in candidates if a.asset_type == row["asset_type"]]
            if symbol and len(candidates) != 1:
                raise ValueError(
                    "Activo no registrado o ambiguo; añade el activo y especifica exchange"
                )
            clean = {k: v for k, v in row.items() if k in TransactionInput.model_fields and v != ""}
            clean["asset_id"] = candidates[0].id if candidates else None
            clean["external_id"] = (
                row.get("external_id")
                or "csv:" + hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            )
            item = TransactionInput.model_validate(clean)
            parsed.append(item)
            preview.append({"row": i, "valid": True, "data": item.model_dump(), "error": None})
        except (ValidationError, ValueError) as exc:
            preview.append({"row": i, "valid": False, "error": str(exc)})
    valid = bool(preview) and all(r["valid"] for r in preview)
    if body.confirm:
        if not valid:
            raise HTTPException(422, "Corrige los errores de la vista previa")
        try:
            for item in sorted(parsed, key=lambda t: t.date):
                save_transaction(db, p, item, commit=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"rows": preview, "valid": valid, "imported": len(parsed) if body.confirm else 0}
