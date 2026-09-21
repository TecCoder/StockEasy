from statistics import median
from typing import Any


class SectorValuationService:
    """Explicit supplied point-in-time universe; no synthetic sector history."""

    def aggregate(
        self,
        values: dict[str, float | None],
        on: str,
        universe_id: str,
        taxonomy: str,
        minimum: int = 5,
    ) -> dict[str, Any]:
        eligible = {
            symbol: value
            for symbol, value in values.items()
            if value is not None and 0 < value < float("inf")
        }
        return {
            "date": on,
            "universe_id": universe_id,
            "taxonomy": taxonomy,
            "method": "median_positive_earnings",
            "universe": list(values),
            "included": list(eligible),
            "sample_size": len(eligible),
            "median_pe": median(eligible.values()) if len(eligible) >= minimum else None,
            "warning": None if len(eligible) >= minimum else "Universo insuficiente",
        }
