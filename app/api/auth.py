"""JWT contract verification endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.schemas.auth import CurrentPrincipalResponse
from app.auth.jwt import Principal, get_current_principal


router = APIRouter(prefix="/v1/auth", tags=["authentication"])


@router.get("/me", response_model=CurrentPrincipalResponse)
async def get_current_identity(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CurrentPrincipalResponse:
    """Expose the identity the RAG service extracted from the bearer token."""

    return CurrentPrincipalResponse(
        user_id=principal.user_id,
        roles=sorted(principal.roles, key=lambda role: role.value),
    )
