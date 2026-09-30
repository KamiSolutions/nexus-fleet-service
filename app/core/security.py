"""
Stateless JWT verification — nexus-financials-service is a token
*consumer*, not an issuer. Only nexus-identity-service mints tokens
(app.core.security.create_access_token_for_role there); this module only
decodes and validates, using the same shared secret.
"""

from __future__ import annotations

from typing import Any

import jwt
from jwt import InvalidTokenError

from app.core.config import settings


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or fails validation."""


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc
