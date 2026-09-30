"""
Authentication + scope-based authorization.

Mirrors the frontend's RBAC model: a JWT carries a list of `scopes`
(the `module:action` permission strings from lib/permissions.ts / rbac.py —
e.g. "finance:view", "vehicles:view", "cases:manage") and each route
declares the scopes it requires via `Security(get_current_user, scopes=[...])`.
FastAPI's `SecurityScopes` mechanism handles composing the required-scope
list from the whole dependency chain and surfaces it to us here.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import ValidationError

from app.core.security import TokenError, decode_access_token
from app.schemas.auth import CurrentUser, TokenPayload

# tokenUrl is documentation-only here (points at the eventual login route);
# it does not need to exist yet for this dependency to function.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> CurrentUser:
    """
    Decode the bearer token, validate its claims, and enforce that every
    scope required by the route (and any parent routers/dependencies) is
    present on the token.

    Raises 401 for anything wrong with the token itself, and 403 when the
    token is valid but lacks a required scope — e.g. a DRIVER's token
    (scopes: dashboard:view, vehicles:view) hitting a finance-scoped
    endpoint.
    """
    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        raw_claims = decode_access_token(token)
        payload = TokenPayload.model_validate(raw_claims)
    except (TokenError, ValidationError) as exc:
        raise credentials_exception from exc

    user = CurrentUser(
        user_id=payload.sub,
        tenant_id=payload.tenant_id,
        scopes=payload.scopes,
        role=payload.role,
    )

    missing_scopes = [scope for scope in security_scopes.scopes if not user.has_scope(scope)]
    if missing_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope(s): {', '.join(missing_scopes)}.",
            headers={"WWW-Authenticate": authenticate_value},
        )

    return user
