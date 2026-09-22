import hashlib
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.analytics.valuation import fcf, ratio
from app.models import Asset
from app.models.fundamental import FundamentalFact
from app.providers.base import ProviderError
from app.providers.gateway import Gateway
from app.providers.sec import CONCEPTS, SEC


def fact_dict(f: FundamentalFact) -> dict[str, Any]:
    return {
        "value": str(f.value),
        "provider": f.provider,
        "period_start": f.start,
        "period_end": f.end,
        "filed": f.filed,
        "retrieved_at": f.retrieved_at,
        "fiscal_period": f.fiscal_period,
        "unit": f.unit,
        "accession": f.accession,
        "source_concept": f.source_concept,
        "calculated": False,
    }


class FundamentalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.provider = SEC(Gateway(db))

    def get(self, asset: Asset, period: str = "annual", refresh: bool = False) -> dict[str, Any]:
        if asset.asset_type != "STOCK":
            return {
                "period": period,
                "history": [],
                "latest": {},
                "warning": "Los fundamentales de empresa no se aplican a este tipo de activo",
            }
        warning = None
        try:
            if not asset.cik:
                asset.cik = self.provider.resolve_cik(asset.symbol)
                self.db.commit()
            response = self.provider.get_historical_fundamentals(asset.cik, refresh)
            warning = response.warning
            us = response.data.get("facts", {}).get("us-gaap", {})
            fact_rows: dict[str, dict[str, Any]] = {}
            for concept, candidates in CONCEPTS.items():
                for tag in candidates:
                    for unit, entries in us.get(tag, {}).get("units", {}).items():
                        if unit not in {asset.currency, asset.currency + "/shares", "shares"}:
                            continue
                        for entry in entries:
                            if entry.get("form") not in {
                                "10-K",
                                "10-Q",
                                "10-K/A",
                                "10-Q/A",
                            } or not entry.get("filed"):
                                continue
                            identity = [
                                asset.id,
                                tag,
                                unit,
                                entry.get("start"),
                                entry["end"],
                                entry["filed"],
                                entry["accn"],
                            ]
                            key = hashlib.sha256(str(identity).encode()).hexdigest()
                            fact_rows[key] = {
                                "id": key,
                                "asset_id": asset.id,
                                "concept": concept,
                                "taxonomy": "us-gaap",
                                "source_concept": tag,
                                "unit": unit,
                                "value": Decimal(str(entry["val"])),
                                "start": date.fromisoformat(entry["start"])
                                if entry.get("start")
                                else None,
                                "end": date.fromisoformat(entry["end"]),
                                "filed": date.fromisoformat(entry["filed"]),
                                "accession": entry["accn"],
                                "fiscal_period": entry.get("fp", ""),
                                "provider": "sec",
                                "retrieved_at": response.retrieved_at,
                            }
            rows_to_save = list(fact_rows.values())
            dialect = self.db.get_bind().dialect.name
            if dialect in {"postgresql", "sqlite"}:
                insert = postgresql_insert if dialect == "postgresql" else sqlite_insert
                for offset in range(0, len(rows_to_save), 50):
                    statement = insert(FundamentalFact).values(rows_to_save[offset : offset + 50])
                    update = {
                        column.name: getattr(statement.excluded, column.name)
                        for column in FundamentalFact.__table__.columns
                        if column.name not in {"id", "valuation_basis"}
                    }
                    self.db.execute(
                        statement.on_conflict_do_update(
                            index_elements=[FundamentalFact.id], set_=update
                        )
                    )
            else:
                for row in rows_to_save:
                    self.db.merge(FundamentalFact(**row))
            self.db.commit()
        except (ProviderError, ValueError, KeyError, TypeError) as exc:
            warning = str(exc) if isinstance(exc, ProviderError) else "SEC: formato no reconocido"
        facts = self.db.scalars(
            select(FundamentalFact)
            .where(FundamentalFact.asset_id == asset.id, FundamentalFact.filed <= date.today())
            .order_by(FundamentalFact.filed, FundamentalFact.accession)
        ).all()
        rows: dict[date, dict[str, FundamentalFact]] = {}
        for fact in facts:
            duration = (fact.end - fact.start).days if fact.start else 0
            valid = (330 <= duration <= 380) if period == "annual" else (70 <= duration <= 105)
            if not valid and fact.start:
                continue
            row = rows.setdefault(fact.end, {})
            prior = row.get(fact.concept)
            # Prefer the documented tag within the same filing date.
            if (
                prior
                and prior.filed == fact.filed
                and CONCEPTS[fact.concept].index(prior.source_concept)
                < CONCEPTS[fact.concept].index(fact.source_concept)
            ):
                continue
            row[fact.concept] = fact
        history = []
        for end, row in sorted(rows.items()):
            if not any(f.start for f in row.values()):
                continue
            metrics = {k: fact_dict(f) for k, f in row.items()}
            ocf, capex = row.get("operating_cash_flow"), row.get("capex")
            if ocf and capex and ocf.start == capex.start and ocf.unit == capex.unit:
                value = fcf(ocf.value, capex.value)
                metrics["fcf"] = {
                    "value": str(value),
                    "calculated": True,
                    "formula": "Operating cash flow - CapEx",
                    "unit": ocf.unit,
                    "inputs": [fact_dict(ocf), fact_dict(capex)],
                    "period_end": end,
                }
            for name, numerator, denominator in [
                ("gross_margin", "gross_profit", "revenue"),
                ("operating_margin", "operating_income", "revenue"),
                ("net_margin", "net_income", "revenue"),
            ]:
                n, d = row.get(numerator), row.get(denominator)
                if n and d and n.start == d.start and n.unit == d.unit:
                    v = ratio(n.value, d.value, True)
                    metrics[name] = {
                        "value": str(v) if v is not None else None,
                        "unit": "ratio",
                        "formula": f"{numerator}/{denominator}",
                        "calculated": True,
                        "inputs": [fact_dict(n), fact_dict(d)],
                    }
            history.append({"date": end, "metrics": metrics})
        return {
            "period": period,
            "history": history,
            "latest": history[-1]["metrics"] if history else {},
            "warning": warning,
        }
