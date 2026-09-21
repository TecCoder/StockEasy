from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from app.core.config import settings
from app.providers.base import PriceBar, ProviderError, ProviderResult
from app.providers.gateway import Gateway


class AlphaVantage:
    name = "alpha_vantage"

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def request(
        self, function: str, ttl: int, refresh: bool = False, **params: Any
    ) -> ProviderResult:
        if not settings.alpha_vantage_api_key:
            raise ProviderError("Alpha Vantage: falta API key")
        return self.gateway.get(
            self.name,
            "https://www.alphavantage.co/query",
            {"function": function, "apikey": settings.alpha_vantage_api_key, **params},
            ttl=ttl,
            refresh=refresh,
        )

    def search_assets(self, query: str) -> ProviderResult:
        r = self.request("SYMBOL_SEARCH", settings.profile_ttl, keywords=query)
        r.data = [
            {
                "symbol": x["1. symbol"],
                "name": x["2. name"],
                "asset_type": {"ETF": "ETF", "Mutual Fund": "MUTUAL_FUND"}.get(
                    x["3. type"], "STOCK"
                ),
                "exchange": x.get("4. region", "UNKNOWN"),
                "currency": x["8. currency"],
                "provider": self.name,
                "provider_asset_id": x["1. symbol"],
            }
            for x in r.data.get("bestMatches", [])
        ]
        return r

    def get_quote(self, symbol: str, currency: str, refresh: bool = False) -> ProviderResult:
        r = self.request("GLOBAL_QUOTE", settings.quote_ttl, refresh, symbol=symbol)
        x = r.data.get("Global Quote", {})
        if not x.get("05. price"):
            raise ProviderError("Alpha Vantage: cotización no disponible")
        r.data = {
            "price": x["05. price"],
            "date": x["07. latest trading day"],
            "change_percent": x.get("10. change percent", "").rstrip("%") or None,
            "currency": currency,
        }
        return r

    def get_historical_prices(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult:
        r = self.request(
            "TIME_SERIES_DAILY", settings.history_ttl, refresh, symbol=symbol, outputsize="compact"
        )
        r.data = [
            PriceBar(
                date=date.fromisoformat(day),
                currency=currency,
                open=Decimal(x["1. open"]),
                high=Decimal(x["2. high"]),
                low=Decimal(x["3. low"]),
                close=Decimal(x["4. close"]),
                volume=Decimal(x["5. volume"]),
            )
            for day, x in r.data.get("Time Series (Daily)", {}).items()
        ]
        if not r.data:
            raise ProviderError("Alpha Vantage: histórico no disponible")
        return r

    def get_company_profile(self, symbol: str) -> ProviderResult:
        return self.request("OVERVIEW", settings.profile_ttl, symbol=symbol)


class FMP:
    name = "fmp"

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def request(self, path: str, ttl: int, refresh: bool = False, **params: Any) -> ProviderResult:
        if not settings.fmp_api_key:
            raise ProviderError("FMP: falta API key")
        return self.gateway.get(
            self.name,
            f"https://financialmodelingprep.com/stable/{path}",
            {"apikey": settings.fmp_api_key, **params},
            ttl=ttl,
            refresh=refresh,
        )

    def search_assets(self, query: str) -> ProviderResult:
        r = self.request("search-symbol", settings.profile_ttl, query=query, limit=15)
        r.data = [
            {
                "symbol": x["symbol"],
                "name": x["name"],
                "asset_type": "STOCK",
                "exchange": x.get("exchangeShortName") or x.get("exchange") or "UNKNOWN",
                "currency": x.get("currency", "USD"),
                "provider": self.name,
                "provider_asset_id": x["symbol"],
            }
            for x in r.data
        ]
        return r

    def get_quote(self, symbol: str, currency: str, refresh: bool = False) -> ProviderResult:
        r = self.request("quote", settings.quote_ttl, refresh, symbol=symbol)
        if not r.data:
            raise ProviderError("FMP: cotización no disponible")
        x = r.data[0]
        r.data = {
            "price": str(x["price"]),
            "currency": currency,
            "date": datetime.fromtimestamp(x["timestamp"], UTC).date().isoformat(),
            "change_percent": x.get("changePercentage"),
            "market_cap": x.get("marketCap"),
        }
        return r

    def get_historical_prices(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult:
        r = self.request("historical-price-eod/full", settings.history_ttl, refresh, symbol=symbol)
        r.data = [
            PriceBar(
                date=date.fromisoformat(x["date"]),
                currency=currency,
                open=Decimal(str(x["open"])),
                high=Decimal(str(x["high"])),
                low=Decimal(str(x["low"])),
                close=Decimal(str(x["close"])),
                volume=Decimal(str(x["volume"])),
                adjustment="unknown",
            )
            for x in r.data
        ]
        return r

    def get_company_profile(self, symbol: str) -> ProviderResult:
        return self.request("profile", settings.profile_ttl, symbol=symbol)


class EODHD:
    name = "eodhd"

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def request(self, path: str, ttl: int, refresh: bool = False, **params: Any) -> ProviderResult:
        if not settings.eodhd_api_key:
            raise ProviderError("EODHD: falta API key")
        return self.gateway.get(
            self.name,
            f"https://eodhd.com/api/{path}",
            {"api_token": settings.eodhd_api_key, "fmt": "json", **params},
            ttl=ttl,
            refresh=refresh,
        )

    def search_assets(self, query: str) -> ProviderResult:
        r = self.request(
            f"search/{quote(query, safe='')}",
            settings.profile_ttl,
            type="fund",
            limit=20,
        )
        r.data = [
            {
                "symbol": x["Code"],
                "name": x["Name"],
                "asset_type": "ETF" if str(x.get("Type", "")).upper() == "ETF" else "MUTUAL_FUND",
                "exchange": x.get("Exchange") or "UNKNOWN",
                "currency": (x.get("Currency") or "EUR").upper(),
                "provider": self.name,
                "provider_asset_id": f"{x['Code']}.{x['Exchange']}",
            }
            for x in r.data
            if x.get("Code") and x.get("Exchange") and x.get("Name")
        ]
        return r

    def get_quote(self, symbol: str, currency: str, refresh: bool = False) -> ProviderResult:
        start = date.today() - timedelta(days=14)
        r = self.request(
            f"eod/{quote(symbol, safe='.-')}",
            settings.quote_ttl,
            refresh,
            **{"from": start.isoformat(), "to": date.today().isoformat(), "order": "d"},
        )
        if not isinstance(r.data, list) or not r.data:
            raise ProviderError("EODHD: NAV no disponible")
        latest = r.data[0]
        previous = r.data[1] if len(r.data) > 1 else None
        current = Decimal(str(latest["adjusted_close"] or latest["close"]))
        prior = Decimal(str(previous["adjusted_close"] or previous["close"])) if previous else None
        change = ((current / prior) - 1) * 100 if prior else None
        r.data = {
            "price": str(current),
            "currency": currency,
            "date": latest["date"],
            "change_percent": str(change) if change is not None else None,
        }
        return r

    def get_historical_prices(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult:
        start = date.today() - timedelta(days=366)
        r = self.request(
            f"eod/{quote(symbol, safe='.-')}",
            settings.history_ttl,
            refresh,
            **{"from": start.isoformat(), "to": date.today().isoformat(), "order": "a"},
        )
        if not isinstance(r.data, list):
            raise ProviderError("EODHD: histórico de NAV no disponible")
        r.data = [
            PriceBar(
                date=date.fromisoformat(x["date"]),
                currency=currency,
                open=Decimal(str(x["open"])) if x.get("open") is not None else None,
                high=Decimal(str(x["high"])) if x.get("high") is not None else None,
                low=Decimal(str(x["low"])) if x.get("low") is not None else None,
                close=Decimal(str(x.get("adjusted_close") or x["close"])),
                volume=Decimal(str(x["volume"])) if x.get("volume") is not None else None,
                adjustment="adjusted",
            )
            for x in r.data
        ]
        if not r.data:
            raise ProviderError("EODHD: histórico de NAV no disponible")
        return r

    def get_company_profile(self, symbol: str) -> ProviderResult:
        return self.request(f"fundamentals/{quote(symbol, safe='.-')}", settings.profile_ttl)


class CoinGecko:
    name = "coingecko"

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def request(self, path: str, ttl: int, refresh: bool = False, **params: Any) -> ProviderResult:
        if not settings.coingecko_api_key:
            raise ProviderError("CoinGecko: falta Demo API key")
        return self.gateway.get(
            self.name,
            f"https://api.coingecko.com/api/v3/{path}",
            params,
            {"x-cg-demo-api-key": settings.coingecko_api_key},
            ttl,
            refresh,
        )

    def search_assets(self, query: str) -> ProviderResult:
        r = self.request("search", settings.profile_ttl, query=query)
        r.data = [
            {
                "symbol": x["symbol"].upper(),
                "name": x["name"],
                "asset_type": "CRYPTO",
                "exchange": "COINGECKO:" + x["id"],
                "currency": "EUR",
                "provider": self.name,
                "provider_asset_id": x["id"],
            }
            for x in r.data.get("coins", [])[:20]
        ]
        return r

    def get_quote(self, symbol: str, currency: str, refresh: bool = False) -> ProviderResult:
        r = self.request(
            "simple/price",
            settings.quote_ttl,
            refresh,
            ids=symbol,
            vs_currencies=currency.lower(),
            include_market_cap="true",
            include_24hr_change="true",
            include_last_updated_at="true",
        )
        x = r.data.get(symbol, {})
        if currency.lower() not in x:
            raise ProviderError("CoinGecko: precio no disponible")
        r.data = {
            "price": str(x[currency.lower()]),
            "currency": currency,
            "date": datetime.fromtimestamp(x["last_updated_at"], UTC).date().isoformat(),
            "change_percent": x.get(currency.lower() + "_24h_change"),
            "market_cap": x.get(currency.lower() + "_market_cap"),
        }
        return r

    def get_market_history(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult:
        r = self.request(
            f"coins/{symbol}/market_chart",
            settings.history_ttl,
            refresh,
            vs_currency=currency.lower(),
            days=365,
            interval="daily",
        )
        r.data = [
            PriceBar(
                date=datetime.fromtimestamp(t / 1000, UTC).date(),
                close=Decimal(str(p)),
                currency=currency,
                adjustment="sampled",
            )
            for t, p in r.data.get("prices", [])
        ]
        return r

    def get_historical_prices(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult:
        return self.get_market_history(symbol, currency, refresh)

    def get_asset_metadata(self, symbol: str) -> ProviderResult:
        return self.request(
            f"coins/{symbol}",
            settings.profile_ttl,
            localization="false",
            tickers="false",
            community_data="false",
            developer_data="false",
        )

    def get_company_profile(self, symbol: str) -> ProviderResult:
        return self.get_asset_metadata(symbol)
