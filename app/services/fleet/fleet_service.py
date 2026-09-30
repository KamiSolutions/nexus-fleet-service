"""
Vehicles / Fleet domain service.

Houses the async data-fetching logic used by the fleet router. Kept
separate from the route module so it can be reused by, e.g., a background
worker or a webhook handler without importing FastAPI. Mirrors the same
concurrent-fan-out pattern nexus-financials-service uses for its policy
providers — here fanning out across vehicle classes instead.

An "overdue for maintenance" vehicle is exactly the kind of "Attention
Required" case the platform's status model (see project master
instructions — never fake an integration/status) is meant to surface
honestly, once this feeds into the Command Centre / Overview aggregation
in nexus-platform-service.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from app.schemas.fleet import FleetSummaryResponse, VehicleClassBreakdown
from app.schemas.tenant import TenantContext

# Vehicle classes a funeral-parlour-network tenant's fleet is typically split into.
_KNOWN_VEHICLE_CLASSES: tuple[str, ...] = ("Hearse", "Family Car", "Support Van", "Bakkie")


async def _fetch_vehicle_class_snapshot(tenant: TenantContext, vehicle_class: str) -> VehicleClassBreakdown:
    """
    Simulates one concurrent, non-blocking call out to a fleet/telematics
    data source for this tenant's vehicle class.

    Replace the body with a real `httpx.AsyncClient` call or DB query; the
    `asyncio.sleep` stands in for network/DB latency so `get_fleet_summary`
    genuinely demonstrates concurrent I/O rather than sequential mocking.
    """
    await asyncio.sleep(random.uniform(0.05, 0.2))

    rng = random.Random(f"{tenant.tenant_id}:{vehicle_class}")
    total = rng.randint(2, 40)
    in_maintenance = rng.randint(0, max(1, total // 5))
    overdue = rng.randint(0, in_maintenance) if in_maintenance else 0

    return VehicleClassBreakdown(
        vehicle_class=vehicle_class,
        total_vehicles=total,
        in_service=total - in_maintenance,
        in_maintenance=in_maintenance,
        overdue_for_maintenance=overdue,
    )


async def get_fleet_summary(tenant: TenantContext) -> FleetSummaryResponse:
    """
    Build the tenant's fleet summary by fanning out to every known vehicle
    class concurrently via `asyncio.gather`, then aggregating the results.
    """
    class_snapshots = await asyncio.gather(
        *(_fetch_vehicle_class_snapshot(tenant, vehicle_class) for vehicle_class in _KNOWN_VEHICLE_CLASSES)
    )

    total_vehicles = sum(c.total_vehicles for c in class_snapshots)
    vehicles_in_maintenance = sum(c.in_maintenance for c in class_snapshots)
    vehicles_overdue_for_maintenance = sum(c.overdue_for_maintenance for c in class_snapshots)

    return FleetSummaryResponse(
        tenant_id=tenant.tenant_id,
        generated_at=datetime.now(timezone.utc),
        total_vehicles=total_vehicles,
        vehicles_in_maintenance=vehicles_in_maintenance,
        vehicles_overdue_for_maintenance=vehicles_overdue_for_maintenance,
        classes=list(class_snapshots),
    )
