from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    login_as: str | None = None
    portal: Literal["employee", "administrator"]
    remember_me: bool = False


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    requested_role: Literal["Employee", "Manager", "HR", "Payroll Administrator"] = "Employee"


class RegisterResponse(BaseModel):
    status: Literal["active", "pending_approval"]
    message: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class CurrentUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role_id: int
    role_name: str
    is_verified: bool
    is_active: bool
    last_login: Optional[datetime] = None
