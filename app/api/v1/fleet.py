"""
Vehicles / Fleet router.

Every route here requires both:
  * a resolved tenant context (`get_tenant_context`) — data isolation, and
  * the `vehicles:view` (or stricter) security scope — RBAC.

`vehicles` matches the module name in the combined role model
(lib/permissions.ts / app/core/rbac.py).

As of this round, this router owns nexus-fleet-service's first real
domain writes: `POST`/`PUT`/`DELETE` on `/vehicles`, each backed by a
real DB table (`app/db/models.py`'s `VehicleModel`) and each emitting a
real audit event to nexus-audit-service
(`app/services/fleet/audit_client.py`).

Deliberately different scope shape from financials/hr/cases/claims:
`vehicles:create` is held only by FLEET_MANAGER (and full-access roles)
— COMPANY_ADMIN does NOT hold it — so `POST` is gated on `create`, but
both `PUT` and `DELETE` are gated on `vehicles:manage`, which COMPANY_ADMIN
*does* hold alongside FLEET_MANAGER. This mirrors the RBAC table's own
existing asymmetry rather than inventing a uniform create/edit/delete
scope-elevation rule across every service.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Security, status

from app.dependencies.auth import get_current_user
from app.dependencies.tenant import get_tenant_context
from app.schemas.auth import CurrentUser
from app.schemas.fleet import (
    FleetSummaryResponse,
    VehicleCreate,
    VehicleDeleteResult,
    VehicleOut,
    VehicleUpdate,
    VehicleWriteResult,
)
from app.schemas.tenant import TenantContext
from app.services.fleet.fleet_service import get_fleet_summary
from app.services.fleet.vehicle_write_service import (
    create_vehicle,
    delete_vehicle,
    list_vehicles,
    update_vehicle,
)

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


@router.get(
    "/vehicles",
    response_model=list[VehicleOut],
    summary="List this tenant's real, written vehicle records",
)
async def read_vehicles(
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: CurrentUser = Security(get_current_user, scopes=["vehicles:view"]),
) -> list[VehicleOut]:
    del current_user
    return await list_vehicles(tenant_id=tenant.tenant_id)


@router.post(
    "/vehicles",
    response_model=VehicleWriteResult,
    status_code=status.HTTP_201_CREATED,
    summary="Create a real vehicle record and emit a real audit event",
)
async def write_new_vehicle(
    payload: VehicleCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: CurrentUser = Security(get_current_user, scopes=["vehicles:create"]),
) -> VehicleWriteResult:
    return await create_vehicle(
        payload,
        tenant_id=tenant.tenant_id,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
    )


@router.put(
    "/vehicles/{vehicle_id}",
    response_model=VehicleWriteResult,
    summary="Update a real vehicle record and emit a real audit event",
)
async def write_vehicle_update(
    vehicle_id: str,
    payload: VehicleUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: CurrentUser = Security(get_current_user, scopes=["vehicles:manage"]),
) -> VehicleWriteResult:
    return await update_vehicle(
        vehicle_id,
        payload,
        tenant_id=tenant.tenant_id,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
    )


@router.delete(
    "/vehicles/{vehicle_id}",
    response_model=VehicleDeleteResult,
    summary="Delete a real vehicle record and emit a real audit event (vehicles:manage only)",
)
async def write_vehicle_delete(
    vehicle_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: CurrentUser = Security(get_current_user, scopes=["vehicles:manage"]),
) -> VehicleDeleteResult:
    return await delete_vehicle(
        vehicle_id,
        tenant_id=tenant.tenant_id,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
    )
