"""Pydantic v2 schemas for the Vehicles / Fleet Logistics domain."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class VehicleClassBreakdown(BaseModel):
    """Fleet figures for a single vehicle class (e.g. hearse, family car)
    within a tenant."""

    model_config = ConfigDict(frozen=True)

    vehicle_class: str
    total_vehicles: int = Field(ge=0)
    in_service: int = Field(ge=0)
    in_maintenance: int = Field(ge=0)
    overdue_for_maintenance: int = Field(ge=0)


class FleetSummaryResponse(BaseModel):
    """Response body for `GET /api/v1/vehicles/summary`."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    generated_at: datetime
    total_vehicles: int = Field(ge=0)
    vehicles_in_maintenance: int = Field(ge=0)
    vehicles_overdue_for_maintenance: int = Field(ge=0)
    classes: list[VehicleClassBreakdown]


# --- Real, DB-backed vehicle writes -----------------------------------------
#
# Distinct from VehicleClassBreakdown/FleetSummaryResponse above (that's
# simulated aggregate data for the summary endpoint). These back the real
# POST/PUT/DELETE /api/v1/vehicles/vehicles endpoints and the `vehicles`
# table in app/db/models.py.


class VehicleStatus(str, Enum):
    IN_SERVICE = "in_service"
    IN_MAINTENANCE = "in_maintenance"
    DECOMMISSIONED = "decommissioned"


class VehicleCreate(BaseModel):
    """Body for `POST /api/v1/vehicles/vehicles`."""

    vehicle_class: str = Field(min_length=1, max_length=120)
    registration_number: str = Field(min_length=1, max_length=32)
    make_model: str = Field(min_length=1, max_length=200)
    status: VehicleStatus = VehicleStatus.IN_SERVICE


class VehicleUpdate(BaseModel):
    """
    Body for `PUT /api/v1/vehicles/vehicles/{vehicle_id}`. Every field is
    optional — only the fields actually sent are changed, everything else
    on the stored record is left untouched.
    """

    vehicle_class: str | None = Field(default=None, min_length=1, max_length=120)
    registration_number: str | None = Field(default=None, min_length=1, max_length=32)
    make_model: str | None = Field(default=None, min_length=1, max_length=200)
    status: VehicleStatus | None = None


class VehicleOut(BaseModel):
    """A real, persisted vehicle record."""

    model_config = ConfigDict(frozen=True)

    id: str
    tenant_id: str
    vehicle_class: str
    registration_number: str
    make_model: str
    status: VehicleStatus
    created_at: datetime
    updated_at: datetime


class AuditWriteStatus(str, Enum):
    """
    Whether the real audit event this write is supposed to emit to
    nexus-audit-service actually landed. Mirrors the project's own
    Operational/Attention Required honesty rule, scoped to this one
    concern: the domain write below always reflects what's really in
    this service's own DB, but `audit` never claims "recorded" unless
    nexus-audit-service genuinely accepted the event — see
    app/services/fleet/audit_client.py.
    """

    RECORDED = "recorded"
    UNAVAILABLE = "unavailable"


class VehicleWriteResult(BaseModel):
    """Response body for `POST` and `PUT` on `/api/v1/vehicles/vehicles`."""

    model_config = ConfigDict(frozen=True)

    vehicle: VehicleOut
    audit: AuditWriteStatus
    audit_detail: str | None = None


class VehicleDeleteResult(BaseModel):
    """Response body for `DELETE /api/v1/vehicles/vehicles/{vehicle_id}`."""

    model_config = ConfigDict(frozen=True)

    deleted_id: str
    audit: AuditWriteStatus
    audit_detail: str | None = None
