"""JWT verification and identity extraction."""

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.config import Settings, get_settings
from app.models.enums import AccessRole


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class Principal:
    """Identity established from a successfully verified access token."""

    user_id: str
    roles: frozenset[AccessRole]


def credentials_error() -> HTTPException:
    """Return a uniform response that does not reveal token failure details."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str, settings: Settings) -> Principal:
    """Validate a backend-issued token and extract trusted role claims."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            leeway=settings.jwt_leeway_seconds,
            options={"require": ["sub", "roles", "iat", "exp", "iss", "aud"]},
        )
        user_id = payload.get("sub")
        raw_roles = payload.get("roles")
        if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 128:
            raise ValueError("Invalid subject")
        if not isinstance(raw_roles, list) or not raw_roles or len(raw_roles) > len(AccessRole):
            raise ValueError("Invalid roles")
        if not all(isinstance(role, str) for role in raw_roles):
            raise ValueError("Invalid role value")
        roles = frozenset(AccessRole(role) for role in raw_roles)
    except (InvalidTokenError, ValueError, TypeError) as exc:
        raise credentials_error() from exc

    return Principal(user_id=user_id.strip(), roles=roles)


async def get_current_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> Principal:
    """FastAPI dependency that authenticates the current request."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_error()
    return decode_access_token(credentials.credentials, get_settings())
