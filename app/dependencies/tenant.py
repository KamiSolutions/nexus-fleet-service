"""
Multi-tenant context resolution.

Design intent
-------------
Nexus Portal serves two deployment shapes from one codebase:

  * "shared"    — small independent parlours, multi-tenant SaaS, isolated by
                  tenant_id inside shared infrastructure (row-level / schema
                  isolation at the DB layer).
  * "dedicated" — large networks (AVBOB/Nyaradzo-scale clones) get a
                  single-tenant deployment with its own database entirely.

`get_tenant_context` is the single seam every route depends on. It never
lets a handler see the raw header — handlers only ever see a resolved,
validated `TenantContext`.

If `X-Tenant-ID` is absent, we fall back to a demo sandbox tenant so the
API is trivially explorable (portfolio/demo use, or a frontend dev running
locally without a provisioned tenant) without special-casing auth.
"""

from __future__ import annotations

import asyncio

from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.schemas.tenant import TenantContext

# --- Tenant registry -------------------------------------------------------
#
# Stand-in for a control-plane lookup (e.g. a Postgres `tenants` table or a
# dedicated tenant-directory microservice). Swap `_TENANT_REGISTRY` and
# `_lookup_tenant_record` for a real async DB/service call — the rest of
# the request pipeline does not need to change, since callers only ever
# depend on `TenantContext`.
_TENANT_REGISTRY: dict[str, dict[str, str]] = {
    settings.DEMO_TENANT_ID: {
        "deployment_mode": "shared",
        "database_dsn": "postgresql+asyncpg://demo:demo@localhost:5432/nexus_demo_sandbox",
        "display_name": "Nexus Demo Sandbox",
    },
    "avbob_prod": {
        "deployment_mode": "dedicated",
        "database_dsn": "postgresql+asyncpg://avbob_app:__secret__@avbob-db.internal:5432/avbob",
        "display_name": "AVBOB (dedicated deployment)",
    },
}


async def _lookup_tenant_record(tenant_id: str) -> dict[str, str] | None:
    """
    Resolve a tenant_id to its deployment record.

    Marked `async` and awaits a no-op sleep(0) to keep the call signature
    identical to what a real network/DB round-trip would look like —
    replace the body with e.g. `await control_plane_db.fetch_one(...)`
    without touching any caller.
    """
    await asyncio.sleep(0)
    return _TENANT_REGISTRY.get(tenant_id)


async def get_tenant_context(
    x_tenant_id: str | None = Header(default=None, alias=settings.TENANT_HEADER_NAME),
) -> TenantContext:
    """
    FastAPI dependency: resolve the calling tenant from the `X-Tenant-ID`
    header, isolating real tenants against the tenant registry and
    falling back to the demo sandbox when the header is missing.
    """
    is_demo = x_tenant_id is None
    tenant_id = x_tenant_id or settings.DEMO_TENANT_ID

    record = await _lookup_tenant_record(tenant_id)

    if record is None:
        # Header was supplied but doesn't match a known, provisioned tenant.
        # Fail closed — never silently fall back to demo data for a
        # tenant_id someone actually specified.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tenant '{tenant_id}'.",
        )

    return TenantContext(
        tenant_id=tenant_id,
        is_demo=is_demo,
        deployment_mode=record["deployment_mode"],
        database_dsn=record["database_dsn"],
        display_name=record["display_name"],
    )
