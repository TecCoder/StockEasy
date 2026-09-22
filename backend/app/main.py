import json
import logging
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth, fundamentals, market, portfolio
from app.api import settings as settings_api
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("stockeasy")


def create_app(shutdown_callback: Callable[[], None] | None = None) -> FastAPI:
    # Vercel Services forwards the original path, including /api.
    api_prefix = "/api"
    app = FastAPI(
        title="StockEasy",
        version="0.1.0-dev",
        docs_url=f"{api_prefix}/docs",
        openapi_url=f"{api_prefix}/openapi.json",
    )
    # The desktop launcher injects this callback. Regular ASGI deployments keep
    # running when a user logs out.
    app.state.shutdown_callback = shutdown_callback
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "testserver",
            "backend",
            "*.vercel.app",
        ],
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.monotonic()
        origin = request.headers.get("origin")
        origin_host = urlsplit(origin).hostname if origin else None
        same_origin = origin_host == request.url.hostname
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and not same_origin
            and origin not in settings.origins
        ):
            return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        # Do not log paths, query strings, body, headers, credentials or tokens.
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "status": response.status_code,
                    "ms": round((time.monotonic() - start) * 1000),
                }
            )
        )
        return response

    @app.get(f"{api_prefix}/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "StockEasy"}

    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(market.router, prefix=api_prefix)
    app.include_router(fundamentals.router, prefix=api_prefix)
    app.include_router(portfolio.router, prefix=api_prefix)
    app.include_router(settings_api.router, prefix=api_prefix)
    return app


app = create_app()
