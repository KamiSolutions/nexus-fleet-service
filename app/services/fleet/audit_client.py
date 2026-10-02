"""
Real audit-event emission to nexus-audit-service, authenticated with
the shared service-to-service credential, alongside every
state-changing write this service performs (create/update/delete a
vehicle) — same pattern established in nexus-financials-service's and
nexus-hr-service's `audit_client.py`.

Honesty note: this service can't make its own DB write and the
downstream audit event land as one real cross-service transaction
without a saga/outbox pattern that doesn't exist yet (P1, same
limitation nexus-audit-service's own docstrings flag). So the domain
write below always succeeds or fails on its own merits, but the audit
event's own outcome is reported back honestly (`recorded` vs
`unavailable`, with the real reason) rather than assumed — the same
Operational/Attention Required honesty rule this project applies
everywhere else, applied here to one write's audit trail.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.schemas.fleet import AuditWriteStatus


async def record_audit_event(
    client: httpx.AsyncClient,
    *,
    actor_user_id: str,
    actor_role: str | None,
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, str] | None = None,
) -> tuple[AuditWriteStatus, str | None]:
    """
    POST a real audit event to nexus-audit-service, authenticating with the
    shared `X-Service-Key` service credential (see nexus-audit-service's
    app/dependencies/service_auth.py) rather than forwarding the caller's
    own bearer token — this service already knows the acting user's
    identity from its own `current_user`, so it sends that explicitly
    instead of relying on nexus-audit-service to decode a forwarded token.

    Returns `(status, detail)` — `detail` is None only when `status` is
    RECORDED.
    """
    headers = {"X-Service-Key": settings.AUDIT_SERVICE_API_KEY, "X-Tenant-ID": tenant_id}
    body = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "actor_user_id": actor_user_id,
        "actor_role": actor_role,
        "metadata": metadata or {},
    }

    try:
        response = await client.post(
            f"{settings.AUDIT_SERVICE_URL}/api/v1/audit/events",
            json=body,
            headers=headers,
        )
    except httpx.RequestError as exc:
        return AuditWriteStatus.UNAVAILABLE, f"unreachable: {exc.__class__.__name__}"

    if response.status_code == 201:
        return AuditWriteStatus.RECORDED, None

    return AuditWriteStatus.UNAVAILABLE, f"nexus-audit-service returned HTTP {response.status_code}"
