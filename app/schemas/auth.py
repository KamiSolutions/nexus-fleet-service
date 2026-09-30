"""Pydantic v2 schemas for authenticated principals and tokens."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TokenPayload(BaseModel):
    """Shape of the decoded JWT claims we actually rely on."""

    model_config = ConfigDict(frozen=True)

    sub: str
    scopes: list[str] = []
    tenant_id: str
    role: str | None = None


class CurrentUser(BaseModel):
    """
    The authenticated principal attached to a request after
    `get_current_user` runs. This is what route handlers should type-hint
    against — never the raw JWT payload.

    `role` is informational only (audit logging, display) — access is
    always decided from `scopes`, never from `role`, so this stays safe
    even if role and scopes ever drift apart.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    tenant_id: str
    scopes: list[str]
    role: str | None = None

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes
