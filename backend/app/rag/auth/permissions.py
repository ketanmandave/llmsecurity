"""SentinelAI-backed endpoint permission adapters for Secure RAG."""

from fastapi import Depends

from app.auth.dependencies import get_administrator_user
from app.models.user import User
from app.rag.auth.jwt import Principal, principal_from_user


def require_admin(
    user: User = Depends(get_administrator_user),
) -> Principal:
    """Require SentinelAI's administrator role and return a RAG principal."""

    return principal_from_user(user)

