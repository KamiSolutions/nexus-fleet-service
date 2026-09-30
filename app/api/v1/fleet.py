"""
Vehicles / Fleet router.

Every route here requires both:
  * a resolved tenant context (`get_tenant_context`) — data isolation, and
  * the `vehicles:view` (or stricter) security scope — RBAC.

`vehicles` matches the module name in the combined role model
(lib/permissions.ts / app/core/rbac.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Security

from app.dependencies.auth import get_current_user
from app.dependencies.tenant import get_tenant_context
from app.schemas.auth import CurrentUser
from app.schemas.fleet import FleetSummaryResponse
from app.schemas.tenant import TenantContext
from app.services.fleet.fleet_service import get_fleet_summary

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get(
    "/summary",
    response_model=FleetSummaryResponse,
    summary="Tenant-wide fleet summary",
)
async def read_fleet_summary(
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: CurrentUser = Security(get_current_user, scopes=["vehicles:view"]),
) -> FleetSummaryResponse:
    """
    Aggregate vehicle-count, maintenance and overdue-maintenance figures
    across every vehicle class for this tenant.

    Restricted to principals holding `vehicles:view` — e.g. FLEET_MANAGER,
    DRIVER, MORTUARY_STAFF, COMPANY_ADMIN, GROUP_ADMIN, or AUDITOR — never
    HR_MANAGER or CLAIMS_OFFICER, whose scopes don't include any
    `vehicles:*` permission.
    """
    # current_user is available for audit logging / row-level narrowing;
    # referenced here to make that intent explicit even though this demo
    # endpoint doesn't yet write an audit trail.
    del current_user
    return await get_fleet_summary(tenant)
