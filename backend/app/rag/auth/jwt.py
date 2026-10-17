"""SentinelAI-authenticated identity adapter for Secure RAG.

The module keeps its historical filename to minimize migration churn, but it no
longer decodes or issues JWTs. SentinelAI verifies the access token, loads the
active user from PostgreSQL, and supplies the trusted database role.
"""

import re
from dataclasses import dataclass

from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.models.user import User


def normalize_role_slug(role_name: str) -> str:
    """Convert a SentinelAI role name into a stable API/audit label."""

    return re.sub(r"[^a-z0-9]+", "_", role_name.casefold()).strip("_")


@dataclass(frozen=True, slots=True)
class Principal:
    """Trusted RAG identity derived from a SentinelAI database user."""

    user_id: str
    role_id: int
    role_name: str
    role_slug: str

    @property
    def role_ids(self) -> frozenset[int]:
        """Return the role-ID collection consumed by ACL database queries."""

        return frozenset({self.role_id})


def principal_from_user(user: User) -> Principal:
    """Map an active SentinelAI user and loaded role to a RAG principal."""

    if user.role is None:
        raise ValueError("Authenticated SentinelAI user has no role")
    return Principal(
        user_id=user.id,
        role_id=user.role.id,
        role_name=user.role.name,
        role_slug=normalize_role_slug(user.role.name),
    )


def get_current_principal(user: User = Depends(get_current_user)) -> Principal:
    """FastAPI dependency backed exclusively by SentinelAI authentication."""

    return principal_from_user(user)

