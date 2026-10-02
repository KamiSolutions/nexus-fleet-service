"""
Application configuration — nexus-fleet-service.

JWT_SECRET_KEY here MUST equal nexus-identity-service's value: this service
verifies tokens statelessly (decode + scope check) rather than calling back
into identity-service per request. That's the whole point of a JWT-based
scheme in a polyrepo split — no synchronous auth-service round-trip on
every request. Keep the secret in lockstep via the shared secrets manager
(nexus-infra), never by copy-pasting .env files by hand.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Nexus Fleet Service"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    API_V1_PREFIX: str = "/api/v1"

    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"  # noqa: S105 - MUST match nexus-identity-service
    JWT_ALGORITHM: str = "HS256"

    DEMO_TENANT_ID: str = "demo_sandbox"
    TENANT_HEADER_NAME: str = "X-Tenant-ID"

    # Real, durable store for this service's own domain writes (vehicles) —
    # see app/db/. SQLite by default for zero-setup dev/test; point this at
    # a Postgres DSN (and install `asyncpg`) for staging/production.
    DATABASE_URL: str = "sqlite+aiosqlite:///./nexus_fleet.db"

    # Where every real write in this service reports its state-changing
    # action, per the project's audit-trail requirement — see
    # app/services/fleet/audit_client.py.
    AUDIT_SERVICE_URL: str = "http://localhost:8007"
    AUDIT_SERVICE_TIMEOUT_SECONDS: float = 3.0

    # Shared static credential sent on the X-Service-Key header when
    # this service POSTs an audit event — MUST equal
    # nexus-audit-service's own AUDIT_SERVICE_API_KEY, same lockstep
    # requirement as JWT_SECRET_KEY. See audit_client.py.
    AUDIT_SERVICE_API_KEY: str = "CHANGE_ME_IN_ENV"  # noqa: S105


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
