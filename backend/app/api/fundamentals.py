from typing import Any, Literal

from fastapi import APIRouter

from app.auth.security import DB, CurrentUser
from app.services.fundamentals import FundamentalService
from app.services.market import own_asset

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
    own_asset(db, user.id, asset_id)
    return {
        "current_pe": None,
        "ttm_pe": None,
        "fy_pe": None,
        "forward_pe": None,
        "historical_pe": [],
        "sector_pe": None,
        "peers": [],
        "warning": "PER no disponible: se requiere EPS TTM completo, fechas de presentación y una base de acciones verificada frente a splits. No se sustituye por EPS FY ni por estimaciones.",
    }
