"""
Real, DB-backed write path for the Vehicles / Fleet Logistics domain.

Distinct from fleet_service.py's `get_fleet_summary`, which aggregates
simulated per-class fleet figures for the read-only summary endpoint —
this module owns Nexus's own real `vehicles` table: part of slice 2 of
the platform's domain writes (financials was slice 1, hr the first
service in slice 2). Every write here also emits a real audit event to
nexus-audit-service via `audit_client.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models import VehicleModel
from app.schemas.fleet import (
    VehicleCreate,
    VehicleDeleteResult,
    VehicleOut,
    VehicleUpdate,
    VehicleWriteResult,
)
from app.services.fleet.audit_client import record_audit_event

_UPDATABLE_FIELDS: tuple[str, ...] = (
    "vehicle_class",
    "registration_number",
    "make_model",
    "status",
)


def _to_out(row: VehicleModel) -> VehicleOut:
    return VehicleOut(
        id=row.id,
        tenant_id=row.tenant_id,
        vehicle_class=row.vehicle_class,
        registration_number=row.registration_number,
        make_model=row.make_model,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_vehicles(*, tenant_id: str) -> list[VehicleOut]:
    """Read-only listing of this tenant's real, written vehicle records, newest first."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(VehicleModel)
            .where(VehicleModel.tenant_id == tenant_id)
            .order_by(VehicleModel.created_at.desc())
        )
        return [_to_out(row) for row in result.scalars().all()]


async def create_vehicle(
    payload: VehicleCreate, *, tenant_id: str, actor_user_id: str, actor_role: str | None
) -> VehicleWriteResult:
    now = datetime.now(timezone.utc)
    row = VehicleModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        vehicle_class=payload.vehicle_class,
        registration_number=payload.registration_number,
        make_model=payload.make_model,
        status=payload.status.value,
        created_at=now,
        updated_at=now,
    )
    async with AsyncSessionLocal() as session:
        session.add(row)
        await session.commit()

    async with httpx.AsyncClient(timeout=settings.AUDIT_SERVICE_TIMEOUT_SECONDS) as client:
        audit_status, audit_detail = await record_audit_event(
            client,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            tenant_id=tenant_id,
            action="vehicle.created",
            resource_type="vehicle",
            resource_id=row.id,
            metadata={"vehicle_class": row.vehicle_class, "registration_number": row.registration_number},
        )

    return VehicleWriteResult(vehicle=_to_out(row), audit=audit_status, audit_detail=audit_detail)


async def update_vehicle(
    vehicle_id: str,
    payload: VehicleUpdate,
    *,
    tenant_id: str,
    actor_user_id: str,
    actor_role: str | None,
) -> VehicleWriteResult:
    async with AsyncSessionLocal() as session:
        row = await session.get(VehicleModel, vehicle_id)
        if row is None or row.tenant_id != tenant_id:
            # Tenant-scoped, fail closed — a real vehicle that belongs to a
            # different tenant is reported identically to one that doesn't
            # exist at all, never leaked as a 403 that would confirm it exists.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")

        changed_fields: dict[str, str] = {}
        for field in _UPDATABLE_FIELDS:
            new_value = getattr(payload, field)
            if new_value is None:
                continue
            new_value = new_value.value if hasattr(new_value, "value") else new_value
            if getattr(row, field) != new_value:
                changed_fields[field] = str(new_value)
            setattr(row, field, new_value)

        row.updated_at = datetime.now(timezone.utc)
        await session.commit()
        out = _to_out(row)

    async with httpx.AsyncClient(timeout=settings.AUDIT_SERVICE_TIMEOUT_SECONDS) as client:
        audit_status, audit_detail = await record_audit_event(
            client,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            tenant_id=tenant_id,
            action="vehicle.updated",
            resource_type="vehicle",
            resource_id=vehicle_id,
            metadata=changed_fields or {"note": "request contained no changed fields"},
        )

    return VehicleWriteResult(vehicle=out, audit=audit_status, audit_detail=audit_detail)


async def delete_vehicle(
    vehicle_id: str, *, tenant_id: str, actor_user_id: str, actor_role: str | None
) -> VehicleDeleteResult:
    async with AsyncSessionLocal() as session:
        row = await session.get(VehicleModel, vehicle_id)
        if row is None or row.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")
        await session.delete(row)
        await session.commit()

    async with httpx.AsyncClient(timeout=settings.AUDIT_SERVICE_TIMEOUT_SECONDS) as client:
        audit_status, audit_detail = await record_audit_event(
            client,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            tenant_id=tenant_id,
            action="vehicle.deleted",
            resource_type="vehicle",
            resource_id=vehicle_id,
        )

    return VehicleDeleteResult(deleted_id=vehicle_id, audit=audit_status, audit_detail=audit_detail)
