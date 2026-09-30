"""nexus-fleet-service — FastAPI application entrypoint.

Owns: vehicle/fleet-logistics endpoints. Verifies JWTs issued by
nexus-identity-service statelessly (shared JWT_SECRET_KEY) — never calls
identity-service synchronously per request.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Nexus Portal — vehicle & fleet-logistics service.",
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT, "service": "nexus-fleet-service"}
