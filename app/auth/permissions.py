"""Role-based endpoint permission checks."""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.jwt import Principal, get_current_principal
from app.models.enums import AccessRole


def has_any_role(principal: Principal, allowed_roles: set[AccessRole]) -> bool:
    """Return whether at least one verified role is authorized."""

    return not principal.roles.isdisjoint(allowed_roles)


async def require_admin(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    """Allow only authenticated administrators to manage documents."""

    if not has_any_role(principal, {AccessRole.ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return principal
