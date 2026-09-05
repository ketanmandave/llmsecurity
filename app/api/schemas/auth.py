"""Authentication-related response schemas."""

from pydantic import BaseModel

from app.models.enums import AccessRole


class CurrentPrincipalResponse(BaseModel):
    user_id: str
    roles: list[AccessRole]
