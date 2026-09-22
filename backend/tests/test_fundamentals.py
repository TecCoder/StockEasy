from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.db.base import utcnow
from app.models import Asset, FundamentalFact, User
from app.providers.base import ProviderResult
from app.services.fundamentals import FundamentalService


def test_sec_facts_are_upserted_without_duplicate_rows(db) -> None:
    user = db.scalar(select(User).where(User.username == "alice"))
    asset = Asset(
        user_id=user.id,
        symbol="TEST",
        name="Test Company",
        asset_type="STOCK",
        exchange="NASDAQ",
        currency="USD",
        cik="0000000001",
    )
    db.add(asset)
    db.commit()

    class StubSEC:
        value = 100

        def get_historical_fundamentals(self, cik, refresh=False):
            assert cik == asset.cik
            return ProviderResult(
                data={
                    "facts": {
                        "us-gaap": {
                            "Revenues": {
                                "units": {
                                    "USD": [
                                        {
                                            "form": "10-K",
                                            "start": "2025-01-01",
                                            "end": "2025-12-31",
                                            "filed": "2026-02-01",
                                            "accn": "0001",
                                            "val": self.value,
                                            "fp": "FY",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                },
                provider="sec",
                retrieved_at=utcnow(),
            )

    service = FundamentalService(db)
    provider = StubSEC()
    service.provider = provider
    assert service.get(asset)["latest"]["revenue"]["value"] == "100"
    provider.value = 125
    assert service.get(asset)["latest"]["revenue"]["value"] == "125"
    assert db.scalar(select(func.count()).select_from(FundamentalFact)) == 1
    fact = db.scalar(select(FundamentalFact))
    assert fact.value == Decimal("125")
    assert fact.end == date(2025, 12, 31)
