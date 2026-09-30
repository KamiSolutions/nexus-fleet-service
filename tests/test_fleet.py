"""
RBAC/tenant verification for nexus-fleet-service.

Tokens are minted in-test with raw PyJWT against this service's own
JWT_SECRET_KEY/ALGORITHM (not by importing nexus-identity-service's code —
that repo isn't checked out alongside this one in CI, so cross-repo
imports would only work locally and silently break in the pipeline). This
mirrors exactly what nexus-identity-service actually puts in a token's
`scopes` claim.
"""

import datetime as dt

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

ROLE_SCOPES = {
    "FLEET_MANAGER": ["dashboard:view", "vehicles:view", "vehicles:create", "vehicles:manage", "reports:view"],
    "HR_MANAGER": ["dashboard:view", "employees:view", "employees:create", "hr:view", "hr:create", "hr:approve", "reports:view"],
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


def test_health(client):
    assert client.get("/health").status_code == 200


def test_fleet_manager_gets_summary(client):
    r = client.get("/api/v1/vehicles/summary", headers={"Authorization": f"Bearer {_mint('FLEET_MANAGER')}"})
    assert r.status_code == 200


def test_hr_manager_forbidden_from_fleet(client):
    r = client.get("/api/v1/vehicles/summary", headers={"Authorization": f"Bearer {_mint('HR_MANAGER')}"})
    assert r.status_code == 403


def test_no_token_unauthorized(client):
    assert client.get("/api/v1/vehicles/summary").status_code == 401


def test_unknown_tenant_not_found(client):
    r = client.get(
        "/api/v1/vehicles/summary",
        headers={"Authorization": f"Bearer {_mint('FLEET_MANAGER')}", "X-Tenant-ID": "does_not_exist"},
    )
    assert r.status_code == 404
