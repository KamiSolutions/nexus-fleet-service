"""Pydantic v2 schemas describing a resolved tenant context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TenantContext(BaseModel):
    """
    The resolved, request-scoped tenant identity.

    Every request handler that touches tenant-owned data should depend on
    this via `get_tenant_context` rather than reading the raw header, so
    isolation logic lives in exactly one place.
    """

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    is_demo: bool
    deployment_mode: str  # "shared" (multi-tenant SaaS) | "dedicated" (single-tenant)
    database_dsn: str
    display_name: str
