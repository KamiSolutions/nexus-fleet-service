"""Pydantic v2 schemas for the Vehicles / Fleet Logistics domain."""

from __future__ import annotations

from datetime import datetime

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
