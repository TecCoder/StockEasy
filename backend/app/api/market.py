from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.auth.security import DB, CurrentUser
from app.core.config import settings
from app.models import ApiCache, Asset, ProviderUsage, Watchlist, WatchlistAsset
from app.providers.gateway import LIMITS
from app.schemas.market import AssetCreate, AssetOut, ManualPrice, WatchlistCreate, WatchlistItem
from app.services.market import MarketService, import_asset, manual_price, own_asset

router = APIRouter(tags=["Assets and watchlists"])


@router.get("/assets/{asset_id}/indicators")
def technical_indicators(asset_id: str, user: CurrentUser, db: DB) -> dict[str, Any]:
    from app.analytics.technical import indicators, sma

    history = MarketService(db).history(own_asset(db, user.id, asset_id))
    rows = history["items"]
    result = indicators([float(r["close"]) for r in rows])
    if rows and all(r["volume"] is not None for r in rows):
        result["AverageVolume20"] = sma([float(r["volume"]) for r in rows], 20)
    return {"dates": [r["date"] for r in rows], "series": result, "warning": history["warning"]}


@router.get("/assets/search")
def search_assets(
    user: CurrentUser,
    db: DB,
    q: str = Query(min_length=1, max_length=100),
    asset_type: str | None = None,
) -> dict[str, Any]:
    return MarketService(db).search(user.id, q, asset_type)


@router.get("/assets", response_model=list[AssetOut])
def list_assets(user: CurrentUser, db: DB) -> Any:
    return db.scalars(select(Asset).where(Asset.user_id == user.id).order_by(Asset.symbol)).all()


@router.post("/assets", response_model=AssetOut)
def add_asset(body: AssetCreate, user: CurrentUser, db: DB) -> Asset:
    return import_asset(db, user.id, body)


@router.get("/assets/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, user: CurrentUser, db: DB) -> Asset:
    return own_asset(db, user.id, asset_id)


@router.get("/assets/{asset_id}/quote")
def quote(asset_id: str, user: CurrentUser, db: DB, refresh: bool = False) -> dict[str, Any]:
    return MarketService(db).quote(own_asset(db, user.id, asset_id), refresh)


@router.get("/assets/{asset_id}/prices")
def history(asset_id: str, user: CurrentUser, db: DB, refresh: bool = False) -> dict[str, Any]:
    return MarketService(db).history(own_asset(db, user.id, asset_id), refresh)


@router.post("/assets/{asset_id}/prices")
def add_manual_price(asset_id: str, body: ManualPrice, user: CurrentUser, db: DB) -> dict[str, Any]:
    return manual_price(db, own_asset(db, user.id, asset_id), body.date, body.close)


def own_watchlist(db: DB, user: CurrentUser, watchlist_id: str) -> Watchlist:
    watchlist = db.scalar(
        select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
    )
    if watchlist is None:
        raise HTTPException(404, "Watchlist no encontrada")
    return watchlist


@router.get("/watchlists")
def list_watchlists(user: CurrentUser, db: DB) -> list[dict[str, Any]]:
    return [
        {"id": w.id, "name": w.name, "comment": w.comment}
        for w in db.scalars(select(Watchlist).where(Watchlist.user_id == user.id))
    ]


@router.post("/watchlists")
def create_watchlist(body: WatchlistCreate, user: CurrentUser, db: DB) -> dict[str, str]:
    w = Watchlist(user_id=user.id, **body.model_dump())
    db.add(w)
    db.commit()
    return {"id": w.id, "name": w.name, "comment": w.comment}


@router.get("/watchlists/{watchlist_id}/items")
def watchlist_items(watchlist_id: str, user: CurrentUser, db: DB) -> list[dict[str, Any]]:
    own_watchlist(db, user, watchlist_id)
    items = db.scalars(
        select(WatchlistAsset)
        .where(WatchlistAsset.watchlist_id == watchlist_id)
        .order_by(WatchlistAsset.position)
    )
    return [
        {
            "asset": AssetOut.model_validate(own_asset(db, user.id, i.asset_id)).model_dump(),
            "comment": i.comment,
            "tags": i.tags,
            "position": i.position,
            "added_at": i.added_at,
        }
        for i in items
    ]


@router.post("/watchlists/{watchlist_id}/items")
def add_watchlist_item(
    watchlist_id: str, body: WatchlistItem, user: CurrentUser, db: DB
) -> dict[str, bool]:
    own_watchlist(db, user, watchlist_id)
    own_asset(db, user.id, body.asset_id)
    existing = db.get(WatchlistAsset, (watchlist_id, body.asset_id))
    if existing:
        existing.comment, existing.tags, existing.position = body.comment, body.tags, body.position
    else:
        db.add(WatchlistAsset(watchlist_id=watchlist_id, **body.model_dump()))
    db.commit()
    return {"ok": True}


@router.delete("/watchlists/{watchlist_id}/items/{asset_id}")
def delete_watchlist_item(
    watchlist_id: str, asset_id: str, user: CurrentUser, db: DB
) -> dict[str, bool]:
    own_watchlist(db, user, watchlist_id)
    item = db.get(WatchlistAsset, (watchlist_id, asset_id))
    if item:
        db.delete(item)
        db.commit()
    return {"ok": True}


@router.get("/providers")
def provider_status(user: CurrentUser, db: DB) -> list[dict[str, Any]]:
    configured = {
        "alpha_vantage": bool(settings.alpha_vantage_api_key),
        "fmp": bool(settings.fmp_api_key),
        "coingecko": bool(settings.coingecko_api_key),
        "sec": bool(settings.sec_user_agent),
        "frankfurter": True,
    }
    result = []
    for name, limits in LIMITS.items():
        u = db.get(ProviderUsage, name)
        result.append(
            {
                "provider": name,
                "configured": configured[name],
                "limits": {"minute": limits[0], "day": limits[1], "month": limits[2]},
                "requests_today": u.daily_count if u else 0,
                "counter_date": u.day if u else None,
                "last_request": u.last_request if u else None,
                "last_success": u.last_success if u else None,
                "retry_after": u.retry_after if u else None,
                "failures": u.failures if u else 0,
                "cache_entries": db.scalar(
                    select(func.count()).select_from(ApiCache).where(ApiCache.provider == name)
                ),
                "oldest_data": db.scalar(
                    select(func.min(ApiCache.fetched_at)).where(ApiCache.provider == name)
                ),
                "latest_data": db.scalar(
                    select(func.max(ApiCache.fetched_at)).where(ApiCache.provider == name)
                ),
            }
        )
    return result
