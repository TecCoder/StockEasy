from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import Asset, AssetPrice, ProviderMapping
from app.providers.base import MarketDataProvider, ProviderError, ProviderResult
from app.providers.gateway import Gateway
from app.providers.market import EODHD, FMP, AlphaVantage, CoinGecko
from app.providers.sec import SEC
from app.schemas.market import AssetCreate, AssetOut


def own_asset(db: Session, user_id: str, asset_id: str) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id))
    if asset is None:
        raise HTTPException(404, "Activo no encontrado")
    return asset


def import_asset(db: Session, user_id: str, body: AssetCreate) -> Asset:
    asset = db.scalar(
        select(Asset).where(
            Asset.user_id == user_id,
            Asset.symbol == body.symbol,
            Asset.exchange == body.exchange,
            Asset.asset_type == body.asset_type,
        )
    )
    if asset is None:
        asset = Asset(user_id=user_id, **body.model_dump(exclude={"provider", "provider_asset_id"}))
        db.add(asset)
        db.flush()
    if body.provider != "manual":
        if body.asset_type == "CRYPTO" and not body.provider_asset_id:
            raise HTTPException(422, "Crypto requiere el identificador de CoinGecko")
        db.merge(
            ProviderMapping(
                asset_id=asset.id,
                provider=body.provider,
                provider_symbol=body.symbol,
                provider_asset_id=body.provider_asset_id or body.symbol,
            )
        )
        # SEC supplies the authoritative CIK and fundamentals, while FMP supplies
        # market prices. Keep both mappings when a US company is imported from EDGAR.
        if body.provider == "sec" and body.asset_type == "STOCK":
            db.merge(
                ProviderMapping(
                    asset_id=asset.id,
                    provider="fmp",
                    provider_symbol=body.symbol,
                    provider_asset_id=body.symbol,
                )
            )
    db.commit()
    return asset


class MarketService:
    def __init__(self, db: Session, providers: list[MarketDataProvider] | None = None) -> None:
        self.db = db
        gateway = Gateway(db)
        self.sec = SEC(gateway)
        self.providers: list[MarketDataProvider] = (
            providers
            if providers is not None
            else [AlphaVantage(gateway), FMP(gateway), EODHD(gateway), CoinGecko(gateway)]
        )

    def search(self, user_id: str, query: str, asset_type: str | None = None) -> dict[str, Any]:
        local = self.db.scalars(
            select(Asset)
            .where(
                Asset.user_id == user_id,
                or_(Asset.symbol.ilike(f"%{query}%"), Asset.name.ilike(f"%{query}%")),
            )
            .limit(30)
        ).all()
        results = [
            {**AssetOut.model_validate(a).model_dump(), "provider": "local"}
            for a in local
            if not asset_type or a.asset_type == asset_type
        ]
        errors = []
        if asset_type in {None, "STOCK"}:
            try:
                response = self.sec.search_companies(query)
                results.extend(response.data)
                if response.warning:
                    errors.append(response.warning)
            except (ProviderError, KeyError, ValueError, TypeError) as exc:
                errors.append(
                    str(exc) if isinstance(exc, ProviderError) else "sec: formato no reconocido"
                )
        for provider in self.providers:
            if asset_type == "CRYPTO" and provider.name != "coingecko":
                continue
            if asset_type != "CRYPTO" and provider.name == "coingecko":
                continue
            if provider.name == "eodhd" and asset_type not in {"ETF", "MUTUAL_FUND"}:
                continue
            if asset_type == "MUTUAL_FUND" and provider.name != "eodhd":
                continue
            if asset_type == "STOCK" and provider.name == "eodhd":
                continue
            try:
                response = provider.search_assets(query)
                results.extend(response.data)
                if response.warning:
                    errors.append(response.warning)
            except (ProviderError, KeyError, ValueError, TypeError) as exc:
                errors.append(
                    str(exc)
                    if isinstance(exc, ProviderError)
                    else f"{provider.name}: formato no reconocido"
                )
        return {"items": results, "warnings": errors}

    def fetch(self, asset: Asset, kind: str, refresh: bool = False) -> ProviderResult:
        errors = []
        mappings = {
            m.provider: m
            for m in self.db.scalars(
                select(ProviderMapping).where(ProviderMapping.asset_id == asset.id)
            )
        }
        candidates = [p for p in self.providers if p.name in mappings]
        # Only explicit mappings are safe: never assume symbols match across exchanges/providers.
        for provider in candidates:
            mapping = mappings[provider.name]
            symbol = (
                mapping.provider_asset_id
                if asset.asset_type == "CRYPTO" or provider.name == "eodhd"
                else mapping.provider_symbol
            )
            try:
                if kind == "history":
                    result = provider.get_historical_prices(symbol, asset.currency, refresh)
                elif kind == "profile":
                    result = provider.get_company_profile(symbol)
                else:
                    result = provider.get_quote(symbol, asset.currency, refresh)
                return result
            except (ProviderError, KeyError, ValueError, TypeError) as exc:
                errors.append(
                    str(exc)
                    if isinstance(exc, ProviderError)
                    else f"{provider.name}: formato no reconocido"
                )
        raise ProviderError(
            "; ".join(errors)
            or "Sin proveedor automático vinculado. Puedes registrar precios manuales."
        )

    def history(self, asset: Asset, refresh: bool = False) -> dict[str, Any]:
        warning = None
        stale = False
        try:
            response = self.fetch(asset, "history", refresh)
            warning, stale = response.warning, response.stale
            for bar in response.data:
                existing = self.db.scalar(
                    select(AssetPrice).where(
                        AssetPrice.asset_id == asset.id,
                        AssetPrice.date == bar.date,
                        AssetPrice.provider == response.provider,
                    )
                )
                if existing:
                    for k, v in asdict(bar).items():
                        setattr(existing, k, v)
                    existing.retrieved_at = response.retrieved_at
                else:
                    self.db.add(
                        AssetPrice(
                            asset_id=asset.id,
                            provider=response.provider,
                            retrieved_at=response.retrieved_at,
                            **asdict(bar),
                        )
                    )
            self.db.commit()
        except ProviderError as exc:
            warning, stale = str(exc), True
        rows = self.db.scalars(
            select(AssetPrice)
            .where(AssetPrice.asset_id == asset.id)
            .order_by(AssetPrice.date, AssetPrice.retrieved_at)
        ).all()
        # Most recently retrieved observation per day. Each row still exposes its source/basis.
        by_date = {row.date: row for row in rows}
        items = [price_dict(by_date[d]) for d in sorted(by_date)]
        return {
            "items": items,
            "warning": warning,
            "stale": stale,
            "coverage_start": items[0]["date"] if items else None,
            "coverage_end": items[-1]["date"] if items else None,
        }

    def quote(self, asset: Asset, refresh: bool = False) -> dict[str, Any]:
        try:
            response = self.fetch(asset, "quote", refresh)
            return {
                **response.data,
                "provider": response.provider,
                "retrieved_at": response.retrieved_at,
                "stale": response.stale,
                "warning": response.warning,
            }
        except ProviderError as exc:
            row = self.db.scalar(
                select(AssetPrice)
                .where(AssetPrice.asset_id == asset.id, AssetPrice.date <= date.today())
                .order_by(AssetPrice.date.desc(), AssetPrice.retrieved_at.desc())
            )
            return {
                "price": str(row.close) if row else None,
                "date": row.date if row else None,
                "provider": row.provider if row else None,
                "currency": asset.currency,
                "retrieved_at": row.retrieved_at if row else None,
                "stale": True,
                "warning": str(exc),
            }


def price_dict(row: AssetPrice) -> dict[str, Any]:
    return {
        key: value.isoformat()
        if isinstance(value, (date, datetime))
        else str(value)
        if isinstance(value, Decimal)
        else value
        for key in (
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "currency",
            "provider",
            "adjustment",
            "retrieved_at",
        )
        for value in [getattr(row, key)]
    }


def manual_price(
    db: Session, asset: Asset, day: date, close: Decimal, valuation_basis: str | None = None
) -> dict[str, Any]:
    row = db.scalar(
        select(AssetPrice).where(
            AssetPrice.asset_id == asset.id, AssetPrice.date == day, AssetPrice.provider == "manual"
        )
    )
    if row is None:
        row = AssetPrice(
            asset_id=asset.id,
            date=day,
            currency=asset.currency,
            provider="manual",
            close=close,
            adjustment="raw",
        )
        db.add(row)
    else:
        row.close, row.retrieved_at = close, utcnow().astimezone(UTC)
    row.valuation_basis = valuation_basis or None
    db.commit()
    return price_dict(row)
