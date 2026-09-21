from datetime import date as DateValue
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.market import Currency, NonNegativeDecimal, PositiveDecimal

TransactionType = Literal[
    "BUY",
    "SELL",
    "DIVIDEND",
    "FEE",
    "DEPOSIT",
    "WITHDRAWAL",
    "SPLIT",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "INTEREST",
]


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    base_currency: Currency = "EUR"


class TransactionInput(BaseModel):
    asset_id: str | None = None
    date: DateValue
    transaction_type: TransactionType
    quantity: PositiveDecimal = Decimal(1)
    price: NonNegativeDecimal = Decimal(0)
    currency: Currency = "EUR"
    fees: NonNegativeDecimal = Decimal(0)
    taxes: NonNegativeDecimal = Decimal(0)
    fx_rate: PositiveDecimal | None = None
    broker: str = Field(default="", max_length=128)
    notes: str = Field(default="", max_length=4000)
    external_id: str | None = Field(default=None, max_length=128)

    @field_validator("date")
    @classmethod
    def no_future(cls, value: DateValue) -> DateValue:
        if value > DateValue.today():
            raise ValueError("No se permiten transacciones futuras")
        return value

    @model_validator(mode="after")
    def validate_type(self) -> "TransactionInput":
        kind = self.transaction_type
        if (
            kind in {"BUY", "SELL", "DIVIDEND", "SPLIT", "TRANSFER_IN", "TRANSFER_OUT"}
            and not self.asset_id
        ):
            raise ValueError("Este tipo requiere un activo")
        if kind in {"DEPOSIT", "WITHDRAWAL", "FEE", "INTEREST"} and self.asset_id:
            raise ValueError("Esta operación de efectivo no admite activo")
        if kind in {"DIVIDEND", "FEE", "DEPOSIT", "WITHDRAWAL", "INTEREST"} and self.quantity != 1:
            raise ValueError("Para efectivo/dividendos usa cantidad 1 y precio como importe bruto")
        if kind == "SPLIT" and (self.price != 0 or self.fees != 0 or self.taxes != 0):
            raise ValueError("SPLIT: cantidad es factor new/old; precio y cargos deben ser cero")
        if kind in {"DIVIDEND", "INTEREST"} and self.fees + self.taxes > self.price:
            raise ValueError("Comisiones e impuestos no pueden superar el ingreso")
        if kind in {"TRANSFER_IN", "TRANSFER_OUT"} and (self.fees or self.taxes):
            raise ValueError("Registra los cargos de transferencia con una operación FEE")
        if self.external_id == "":
            self.external_id = None
        return self


class FXInput(BaseModel):
    base: Currency
    quote: Currency
    date: DateValue
    rate: PositiveDecimal

    @model_validator(mode="after")
    def valid(self) -> "FXInput":
        if self.date > DateValue.today() or (self.base == self.quote and self.rate != 1):
            raise ValueError("Fecha o tipo de cambio inválido")
        return self
