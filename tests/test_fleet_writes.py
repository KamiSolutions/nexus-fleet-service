"""
RBAC + persistence + honest audit-degradation tests for the real
POST/PUT/DELETE `/vehicles` endpoints — part of slice 2's writes,
following the same pattern proved in nexus-financials-service's
`test_policy_writes.py`.

Fleet's scope shape is deliberately different from financials/hr: only
`vehicles:create` gates `POST` (FLEET_MANAGER + full-access roles only —
COMPANY_ADMIN does NOT hold `vehicles:create`), while `vehicles:manage`
gates BOTH `PUT` and `DELETE` (FLEET_MANAGER + COMPANY_ADMIN + full-access
roles). This mirrors the RBAC table's own existing asymmetry.

The audit call each write makes genuinely fails here (nexus-audit-service
isn't running during `pytest`), and that's deliberate: it proves the
honest-degradation path for real rather than mocking it.
"""

from __future__ import annotations

import datetime as dt

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

ROLE_SCOPES = {
    "FLEET_MANAGER": ["dashboard:view", "vehicles:view", "vehicles:create", "vehicles:manage"],
    "COMPANY_ADMIN": ["dashboard:view", "vehicles:view", "vehicles:manage"],
    "DRIVER": ["dashboard:view", "vehicles:view"],
}


def _mint(role: str, tenant_id: str = "demo_sandbox") -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": "test-user",
        "scopes": ROLE_SCOPES[role],
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def _auth(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_mint(role)}"}


def _create_payload(**overrides):
    payload = {
        "vehicle_class": "Hearse",
        "registration_number": "CA123-456",
        "make_model": "Mercedes-Benz S-Class",
    }
    payload.update(overrides)
    return payload


def test_fleet_manager_can_create_vehicle(client):
    r = client.post("/api/v1/vehicles/vehicles", json=_create_payload(), headers=_auth("FLEET_MANAGER"))
    assert r.status_code == 201
    body = r.json()
    assert body["vehicle"]["vehicle_class"] == "Hearse"
    assert body["vehicle"]["status"] == "in_service"
    assert body["vehicle"]["tenant_id"] == "demo_sandbox"
    # nexus-audit-service isn't running during pytest — this must stay
    # honest, never a fabricated "recorded".
    assert body["audit"] == "unavailable"
    assert body["audit_detail"]


def test_company_admin_forbidden_from_creating_vehicle(client):
    # COMPANY_ADMIN holds vehicles:manage but not vehicles:create — a
    # deliberate asymmetry already present in the RBAC table.
    r = client.post("/api/v1/vehicles/vehicles", json=_create_payload(), headers=_auth("COMPANY_ADMIN"))
    assert r.status_code == 403


def test_driver_forbidden_from_creating_vehicle(client):
    r = client.post("/api/v1/vehicles/vehicles", json=_create_payload(), headers=_auth("DRIVER"))
    assert r.status_code == 403


def test_created_vehicle_is_listed_and_persisted(client):
    create = client.post(
        "/api/v1/vehicles/vehicles",
        json=_create_payload(registration_number="LIST-001"),
        headers=_auth("FLEET_MANAGER"),
    )
    vehicle_id = create.json()["vehicle"]["id"]

    listing = client.get("/api/v1/vehicles/vehicles", headers=_auth("FLEET_MANAGER"))
    assert listing.status_code == 200
    assert any(v["id"] == vehicle_id for v in listing.json())


def test_company_admin_can_update_vehicle(client):
    create = client.post(
        "/api/v1/vehicles/vehicles",
        json=_create_payload(registration_number="UPD-001"),
        headers=_auth("FLEET_MANAGER"),
    )
    vehicle_id = create.json()["vehicle"]["id"]

    # COMPANY_ADMIN holds vehicles:manage, so unlike create, it CAN update.
    r = client.put(
        f"/api/v1/vehicles/vehicles/{vehicle_id}",
        json={"status": "in_maintenance"},
        headers=_auth("COMPANY_ADMIN"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["vehicle"]["status"] == "in_maintenance"
    assert body["vehicle"]["registration_number"] == "UPD-001"


def test_update_unknown_vehicle_is_404(client):
    r = client.put(
        "/api/v1/vehicles/vehicles/does-not-exist",
        json={"status": "in_maintenance"},
        headers=_auth("FLEET_MANAGER"),
    )
    assert r.status_code == 404


def test_driver_forbidden_from_deleting_vehicle(client):
    create = client.post(
        "/api/v1/vehicles/vehicles",
        json=_create_payload(registration_number="DEL-001"),
        headers=_auth("FLEET_MANAGER"),
    )
    vehicle_id = create.json()["vehicle"]["id"]

    r = client.delete(f"/api/v1/vehicles/vehicles/{vehicle_id}", headers=_auth("DRIVER"))
    assert r.status_code == 403


def test_company_admin_can_delete_vehicle(client):
    # Unlike financials/hr (where delete needs a stronger scope than
    # create), fleet's DELETE and PUT share `vehicles:manage` — the same
    # scope COMPANY_ADMIN holds without holding `vehicles:create`.
    create = client.post(
        "/api/v1/vehicles/vehicles",
        json=_create_payload(registration_number="DEL-002"),
        headers=_auth("FLEET_MANAGER"),
    )
    vehicle_id = create.json()["vehicle"]["id"]

    r = client.delete(f"/api/v1/vehicles/vehicles/{vehicle_id}", headers=_auth("COMPANY_ADMIN"))
    assert r.status_code == 200
    assert r.json()["deleted_id"] == vehicle_id

    listing = client.get("/api/v1/vehicles/vehicles", headers=_auth("FLEET_MANAGER"))
    assert all(v["id"] != vehicle_id for v in listing.json())


def test_delete_unknown_vehicle_is_404(client):
    r = client.delete("/api/v1/vehicles/vehicles/does-not-exist", headers=_auth("FLEET_MANAGER"))
    assert r.status_code == 404


def test_no_token_unauthorized_on_write(client):
    assert client.post("/api/v1/vehicles/vehicles", json=_create_payload()).status_code == 401


def test_unknown_tenant_not_found_on_write(client):
    r = client.post(
        "/api/v1/vehicles/vehicles",
        json=_create_payload(),
        headers={**_auth("FLEET_MANAGER"), "X-Tenant-ID": "does_not_exist"},
    )
    assert r.status_code == 404
