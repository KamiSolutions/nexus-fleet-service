"""nexus-fleet-service — FastAPI application entrypoint.

Owns: vehicle, fleet and logistics endpoints. Verifies JWTs issued by
nexus-identity-service statelessly (shared JWT_SECRET_KEY) — never calls
identity-service synchronously per request.
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import create_all_tables, engine

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Nexus Portal — vehicle & fleet logistics service.",
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


async def _bootstrap_database_async() -> None:
    await create_all_tables()
    # See nexus-identity-service's identical comment (app/main.py): this
    # runs its own throwaway event loop via asyncio.run below, separate
    # from whatever loop actually serves requests afterwards — dispose the
    # pool so no aiosqlite connection opened against that bootstrap loop
    # lingers into a different one later.
    await engine.dispose()


def _bootstrap_database() -> None:
    asyncio.run(_bootstrap_database_async())


_bootstrap_database()


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT, "service": "nexus-fleet-service"}
