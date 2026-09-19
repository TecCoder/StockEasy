from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol


class ProviderError(Exception):
    """Sanitized error that never embeds a URL or API credential."""


@dataclass
class ProviderResult:
    data: Any
    provider: str
    retrieved_at: datetime
    stale: bool = False
    warning: str | None = None


@dataclass
class PriceBar:
    date: date
    close: Decimal
    currency: str
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    volume: Decimal | None = None
    adjustment: str = "raw"


class MarketDataProvider(Protocol):
    name: str

    def search_assets(self, query: str) -> ProviderResult: ...
    def get_quote(self, symbol: str, currency: str, refresh: bool = False) -> ProviderResult: ...
    def get_historical_prices(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult: ...
    def get_company_profile(self, symbol: str) -> ProviderResult: ...


class FundamentalDataProvider(Protocol):
    def get_historical_fundamentals(self, cik: str, refresh: bool = False) -> ProviderResult: ...
    def get_income_statement(self, cik: str) -> ProviderResult: ...
    def get_balance_sheet(self, cik: str) -> ProviderResult: ...
    def get_cash_flow_statement(self, cik: str) -> ProviderResult: ...
    def get_ratios(self, cik: str) -> ProviderResult: ...


class CryptoDataProvider(Protocol):
    def get_quote(self, symbol: str, currency: str, refresh: bool = False) -> ProviderResult: ...
    def get_market_history(
        self, symbol: str, currency: str, refresh: bool = False
    ) -> ProviderResult: ...
    def get_asset_metadata(self, symbol: str) -> ProviderResult: ...
