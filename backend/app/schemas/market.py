from datetime import date as DateValue
from decimal import Decimal
from typing import Annotated, Literal

import pycountry
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


def currency(value: str) -> str:
    value = value.strip().upper()
    if not pycountry.currencies.get(alpha_3=value):
        raise ValueError("Currency must be an ISO 4217 code")
    return value


Currency = Annotated[str, BeforeValidator(currency)]
PositiveDecimal = Annotated[
    Decimal, Field(gt=0, max_digits=30, decimal_places=12, allow_inf_nan=False)
]
NonNegativeDecimal = Annotated[
    Decimal, Field(ge=0, max_digits=30, decimal_places=12, allow_inf_nan=False)
]
AssetType = Literal["STOCK", "ETF", "MUTUAL_FUND", "CRYPTO"]


class AssetCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    asset_type: AssetType = "STOCK"
    exchange: str = Field(default="MANUAL", min_length=1, max_length=64)
    currency: Currency = "EUR"
    provider: Literal["manual", "alpha_vantage", "fmp", "coingecko"] = "manual"
    provider_asset_id: str = Field(default="", max_length=128, pattern=r"^[a-zA-Z0-9._:-]*$")
    cik: str | None = Field(default=None, pattern=r"^\d{1,10}$")

    @field_validator("symbol", "exchange")
    @classmethod
    def normalize(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Cannot be blank")
        return value


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    symbol: str
    name: str
    asset_type: str
    exchange: str
    currency: str
    sector: str | None
    industry: str | None
    country: str | None
    cik: str | None


class ManualPrice(BaseModel):
    date: DateValue
    close: NonNegativeDecimal

    @field_validator("date")
    @classmethod
    def past_date(cls, value: DateValue) -> DateValue:
        if value > DateValue.today():
            raise ValueError("Future prices are not permitted")
        return value


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=2000)


class WatchlistItem(BaseModel):
    asset_id: str
    comment: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)
    position: int = Field(default=0, ge=0)
