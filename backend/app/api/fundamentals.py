from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter
from sqlalchemy import select

from app.analytics.valuation import (
    EPSObservation,
    discrete_quarterly_eps,
    historical_pe,
    valuation_statistics,
)
from app.auth.security import DB, CurrentUser
from app.models import FundamentalFact
from app.services.fundamentals import FundamentalService
from app.services.market import MarketService, own_asset

router = APIRouter(tags=["Fundamentals"])


@router.get("/assets/{asset_id}/fundamentals")
def fundamentals(
    asset_id: str,
    user: CurrentUser,
    db: DB,
    period: Literal["annual", "quarterly"] = "annual",
    refresh: bool = False,
) -> dict[str, Any]:
    return FundamentalService(db).get(own_asset(db, user.id, asset_id), period, refresh)


@router.get("/assets/{asset_id}/valuation")
def valuation(asset_id: str, user: CurrentUser, db: DB) -> dict[str, Any]:
    asset = own_asset(db, user.id, asset_id)
    fundamental_result = FundamentalService(db).get(asset, "quarterly")
    market_result = MarketService(db).history(asset)
    facts = db.scalars(
        select(FundamentalFact)
        .where(
            FundamentalFact.asset_id == asset.id,
            FundamentalFact.concept == "eps",
            FundamentalFact.start.is_not(None),
            FundamentalFact.filed <= date.today(),
        )
        .order_by(FundamentalFact.filed, FundamentalFact.accession)
    ).all()
    basis = "sec:EarningsPerShareDiluted"
    observations = discrete_quarterly_eps(
        [
            EPSObservation(
                start=fact.start,
                end=fact.end,
                filed=fact.filed,
                value=fact.value,
                accession=fact.accession,
                currency=fact.unit.removesuffix("/shares"),
                basis=basis,
            )
            for fact in facts
            if fact.start is not None and fact.unit.endswith("/shares")
        ]
    )
    prices = [
        (date.fromisoformat(item["date"]), Decimal(item["close"]))
        for item in market_result["items"]
        if item["currency"] == asset.currency
    ]
    points = historical_pe(prices, observations, asset.currency, basis)
    available = [point for point in points if point["pe"] is not None]
    latest = available[-1] if available else None
    statistics = valuation_statistics(
        [float(point["pe"]) for point in available],
        float(latest["pe"]) if latest else None,
    )
    warnings = [
        value
        for value in (fundamental_result.get("warning"), market_result.get("warning"))
        if value
    ]
    warnings.append(
        "PER diario calculado como cierre / EPS diluido TTM conocido en esa fecha. "
        "Revisa posibles discontinuidades alrededor de splits."
        if available
        else "PER diario no disponible: hacen falta cuatro trimestres consecutivos de EPS "
        "diluido en la misma moneda y precios diarios compatibles."
    )
    return {
        "current_pe": str(latest["pe"]) if latest else None,
        "ttm_eps": str(latest["eps"]) if latest else None,
        "price_date": latest["price_date"].isoformat() if latest else None,
        "fy_pe": None,
        "forward_pe": None,
        "historical_pe": [
            {
                "date": point["price_date"].isoformat(),
                "price": str(point["price"]),
                "eps_ttm": str(point["eps"]),
                "pe": str(point["pe"]),
                "eps_periods": [
                    {
                        key: value.isoformat() if isinstance(value, date) else value
                        for key, value in period.items()
                    }
                    for period in point["eps_periods"]
                ],
            }
            for point in available
        ],
        "statistics": statistics,
        "sector_pe": None,
        "peers": [],
        "warning": " ".join(dict.fromkeys(warnings)),
    }
