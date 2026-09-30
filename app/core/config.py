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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
