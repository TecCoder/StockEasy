"""Bounded HTTP transport, persistent cache and quotas (one backend worker)."""

import hashlib
import json
import threading
import time
from datetime import UTC, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.market import ApiCache, ProviderUsage
from app.providers.base import ProviderError, ProviderResult

# Local conservative caps, not promises of upstream plan entitlements.
LIMITS = {
    "alpha_vantage": (5, 25, 750),
    "fmp": (20, 250, 7500),
    "eodhd": (10, 20, 600),
    "coingecko": (30, 300, 9000),
    "sec": (60, 5000, 100000),
    "frankfurter": (30, 5000, 100000),
}
LOCK = threading.RLock()


class Gateway:
    def __init__(self, db: Session, client: httpx.Client | None = None) -> None:
        self.db = db
        self.client = client

    def reserve(self, provider: str) -> ProviderUsage:
        with LOCK:
            now = utcnow()
            usage = self.db.get(ProviderUsage, provider)
            if usage is None:
                usage = ProviderUsage(
                    provider=provider,
                    day=now.date().isoformat(),
                    month=now.strftime("%Y-%m"),
                    minute_start=now,
                    minute_count=0,
                    daily_count=0,
                    monthly_count=0,
                    failures=0,
                )
                self.db.add(usage)
            self.db.refresh(usage) if usage not in self.db.new else None
            if usage.day != now.date().isoformat():
                usage.day, usage.daily_count = now.date().isoformat(), 0
            if usage.month != now.strftime("%Y-%m"):
                usage.month, usage.monthly_count = now.strftime("%Y-%m"), 0
            if usage.minute_start.replace(tzinfo=UTC) <= now - timedelta(minutes=1):
                usage.minute_start, usage.minute_count = now, 0
            minute, day, month = LIMITS[provider]
            if usage.retry_after and usage.retry_after.replace(tzinfo=UTC) > now:
                raise ProviderError(f"{provider}: espera activa por límite o fallo del proveedor")
            if (
                usage.minute_count >= minute
                or usage.daily_count >= day
                or usage.monthly_count >= month
            ):
                raise ProviderError(f"{provider}: cuota local alcanzada")
            # SEC conservative 1 request/sec, also across successive sessions.
            if provider == "sec" and usage.last_request:
                delay = 1 - (now - usage.last_request.replace(tzinfo=UTC)).total_seconds()
                if delay > 0:
                    time.sleep(delay)
            usage.minute_count += 1
            usage.daily_count += 1
            usage.monthly_count += 1
            usage.last_request = utcnow()
            self.db.commit()
            return usage

    def get(
        self,
        provider: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        ttl: int = 900,
        refresh: bool = False,
    ) -> ProviderResult:
        params = params or {}
        safe = {
            k: v for k, v in params.items() if k not in {"apikey", "api_key", "api_token", "token"}
        }
        key = hashlib.sha256(json.dumps([provider, url, safe], sort_keys=True).encode()).hexdigest()
        cached = self.db.get(ApiCache, key)
        now = utcnow()
        if cached and not refresh and cached.expires_at.replace(tzinfo=UTC) > now:
            return ProviderResult(cached.payload, provider, cached.fetched_at.replace(tzinfo=UTC))
        try:
            data = self._request(provider, url, params, headers or {})
            now = utcnow()
            self.db.merge(
                ApiCache(
                    key=key,
                    provider=provider,
                    payload=data,
                    fetched_at=now,
                    expires_at=now + timedelta(seconds=ttl),
                )
            )
            self.db.commit()
            return ProviderResult(data, provider, now)
        except ProviderError as exc:
            if cached:
                return ProviderResult(
                    cached.payload, provider, cached.fetched_at.replace(tzinfo=UTC), True, str(exc)
                )
            raise

    def _request(
        self, provider: str, url: str, params: dict[str, Any], headers: dict[str, str]
    ) -> Any:
        for attempt in range(2):
            usage = self.reserve(provider)
            try:
                if self.client:
                    response = self.client.get(url, params=params, headers=headers, timeout=12)
                else:
                    with httpx.Client(timeout=12, follow_redirects=False) as client:
                        response = client.get(url, params=params, headers=headers)
                if response.status_code == 429:
                    retry = response.headers.get("Retry-After", "60")
                    try:
                        seconds = max(1, int(retry))
                    except ValueError:
                        try:
                            seconds = max(
                                1, int((parsedate_to_datetime(retry) - utcnow()).total_seconds())
                            )
                        except (ValueError, TypeError):
                            seconds = 60
                    usage.retry_after = utcnow() + timedelta(seconds=seconds)
                    raise ProviderError(f"{provider}: límite de peticiones del proveedor")
                if response.status_code == 401:
                    usage.retry_after = utcnow() + timedelta(minutes=15)
                    raise ProviderError(f"{provider}: clave inválida")
                if response.status_code in {402, 403}:
                    # A plan restriction may apply to one endpoint or symbol only.
                    # Do not block every request to the provider for fifteen minutes.
                    raise ProviderError(f"{provider}: datos no incluidos en el plan")
                if response.status_code >= 500:
                    raise httpx.ConnectError("Upstream unavailable")
                if response.status_code != 200:
                    raise ProviderError(
                        f"{provider}: respuesta no disponible ({response.status_code})"
                    )
                data = response.json()
                if isinstance(data, dict) and any(
                    k in data for k in ("Error Message", "Information", "Note", "error")
                ):
                    usage.retry_after = utcnow() + timedelta(minutes=15)
                    raise ProviderError(
                        f"{provider}: datos no disponibles; comprueba clave, plan y cuota"
                    )
                if not data:
                    raise ProviderError(f"{provider}: respuesta vacía")
                usage.last_success = utcnow()
                self.db.commit()
                return data
            except (httpx.HTTPError, ValueError):
                usage.failures += 1
                self.db.commit()
                if attempt == 0:
                    time.sleep(0.5 * (2**attempt))
                    continue
                usage.retry_after = utcnow() + timedelta(seconds=30)
                self.db.commit()
                raise ProviderError(f"{provider}: conexión no disponible") from None
            except ProviderError:
                usage.failures += 1
                self.db.commit()
                raise
        raise ProviderError(f"{provider}: no disponible")
