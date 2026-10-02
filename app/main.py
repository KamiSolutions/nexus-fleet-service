"""nexus-fleet-service — FastAPI application entrypoint.

Owns: vehicle, fleet and logistics endpoints. Verifies JWTs issued by
nexus-identity-service statelessly (shared JWT_SECRET_KEY) — never calls
identity-service synchronously per request.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import create_all_tables, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Create tables as a real FastAPI startup event, inside whatever event
    loop is actually about to serve requests — see
    nexus-identity-service's `app/main.py` docstring for the full
    reasoning: the previous import-time `asyncio.run(...)` bootstrap broke
    under a real `uvicorn app.main:app` launch (confirmed against a real
    uvicorn process, not just reasoned about), since uvicorn imports this
    module from inside its own already-running event loop.
    """
    await create_all_tables()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Nexus Portal — vehicle & fleet logistics service.",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT, "service": "nexus-fleet-service"}
