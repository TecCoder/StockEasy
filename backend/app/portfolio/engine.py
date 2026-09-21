"""Deterministic weighted-average ledger. All amounts use Decimal."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

ZERO = Decimal(0)


class Entry(Protocol):
    asset_id: str | None
    date: date
    transaction_type: str
    quantity: Decimal
    price: Decimal
    currency: str
    fees: Decimal
    taxes: Decimal
    fx_rate: Decimal


@dataclass
class Position:
    asset_id: str
    currency: str
    quantity: Decimal = ZERO
    cost: Decimal = ZERO
    cost_base: Decimal = ZERO
    realized: Decimal = ZERO
    realized_base: Decimal = ZERO
    dividends: Decimal = ZERO
    dividends_base: Decimal = ZERO


@dataclass
class Ledger:
    positions: dict[str, Position] = field(default_factory=dict)
    cash: dict[str, Decimal] = field(default_factory=dict)
    contributions: Decimal = ZERO
    external_flows: list[tuple[date, Decimal]] = field(default_factory=list)
    transfer_valuation_missing: bool = False


def reconstruct(entries: list[Entry]) -> Ledger:
    """Entries must be ordered by date and stable ledger sequence; no short sales."""
    ledger = Ledger()
    for e in entries:
        kind, amount, costs = e.transaction_type, e.quantity * e.price, e.fees + e.taxes
        fx = e.fx_rate
        if e.quantity <= 0 or min(e.price, e.fees, e.taxes) < 0 or fx <= 0:
            raise ValueError("Importes inválidos")
        movement = ZERO
        p = None
        if e.asset_id:
            p = ledger.positions.setdefault(e.asset_id, Position(e.asset_id, e.currency))
            if p.currency != e.currency:
                raise ValueError("La moneda de la operación no coincide con la posición")
        if kind in {"BUY", "TRANSFER_IN"}:
            if p is None:
                raise ValueError("Se requiere activo")
            p.quantity += e.quantity
            p.cost += amount + costs
            p.cost_base += (amount + costs) * fx
            if kind == "BUY":
                movement = -amount - costs
            else:
                # Carrying cost is not an external fair-value flow. Performance must be unavailable.
                ledger.transfer_valuation_missing = True
        elif kind in {"SELL", "TRANSFER_OUT"}:
            if p is None or p.quantity < e.quantity:
                raise ValueError("Venta/transferencia superior a la posición disponible")
            removed = p.cost * e.quantity / p.quantity
            removed_base = p.cost_base * e.quantity / p.quantity
            p.quantity -= e.quantity
            p.cost -= removed
            p.cost_base -= removed_base
            if kind == "SELL":
                p.realized += amount - costs - removed
                p.realized_base += (amount - costs) * fx - removed_base
                movement = amount - costs
            else:
                ledger.transfer_valuation_missing = True
        elif kind == "SPLIT":
            if p is None or p.quantity <= 0:
                raise ValueError("No hay posición para aplicar split")
            p.quantity *= e.quantity
        elif kind == "DIVIDEND":
            if p is None:
                raise ValueError("Se requiere activo para dividendo")
            p.dividends += amount - costs
            p.dividends_base += (amount - costs) * fx
            movement = amount - costs
        elif kind == "INTEREST":
            movement = amount - costs
        elif kind == "DEPOSIT":
            movement = amount - costs
            ledger.contributions += amount * fx
            ledger.external_flows.append((e.date, -amount * fx))
        elif kind == "WITHDRAWAL":
            movement = -amount - costs
            ledger.contributions -= amount * fx
            ledger.external_flows.append((e.date, amount * fx))
        elif kind == "FEE":
            movement = -amount - costs
        else:
            raise ValueError("Tipo de transacción desconocido")
        ledger.cash[e.currency] = ledger.cash.get(e.currency, ZERO) + movement
    return ledger
