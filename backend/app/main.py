import json
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth, market
from app.api import settings as settings_api
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("stockeasy")


def create_app() -> FastAPI:
    app = FastAPI(
        title="StockEasy",
        version="0.1.0-dev",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "backend"]
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.monotonic()
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
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

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "StockEasy"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(market.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")
    return app


app = create_app()
