"""SQLAlchemy ORM models backing the real Vehicles/Fleet writes."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VehicleModel(Base):
    """
    A real, tenant-scoped vehicle record — created/updated/deleted via
    `POST/PUT/DELETE /api/v1/vehicles/vehicles`. Distinct from the
    fan-out demo data `fleet_service.get_fleet_summary` still generates
    for `/vehicles/summary` (that endpoint aggregates simulated per-class
    fleet figures; this table is Nexus's own real record of vehicles the
    tenant has actually entered here).
    """

    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vehicle_class: Mapped[str] = mapped_column(String(120), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(32), nullable=False)
    make_model: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "in_service" | "in_maintenance" | "decommissioned"
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
