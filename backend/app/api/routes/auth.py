from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, RefreshTokenRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth_service import AuthService, PUBLIC_REGISTRATION_ROLES
from app.services.audit_log_service import AuditLogService
from app.utils.security import create_access_token, create_refresh_token

router = APIRouter()


@router.get("/registration-roles", response_model=list[str])
def registration_roles() -> list[str]:
    """Return roles users may request without exposing platform roles."""

    return list(PUBLIC_REGISTRATION_ROLES)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    auth_service = AuthService(db)
    try:
        user = auth_service.register(
            payload.name,
            payload.email,
            payload.password,
            payload.requested_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not user.is_active:
        return RegisterResponse(
            status="pending_approval",
            message=(
                f"Your {user.role.name} role request was submitted. "
                "An administrator must approve the account before you can sign in."
            ),
        )

    access_token = create_access_token(user.id, user.role_id)
    refresh_token = create_refresh_token(user.id)
    auth_service._store_refresh_token(user.id, refresh_token)
    return RegisterResponse(
        status="active",
        message="Account created successfully",
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    auth_service = AuthService(db)
    try:
        user, access_token, refresh_token = auth_service.login(payload.email, payload.password, payload.login_as, payload.portal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc
    audit_service = AuditLogService(db)
    audit_service.create_log("login", "success", user_id=user.id, ip_address=request.client.host if request.client else None, details="User logged in")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    auth_service = AuthService(db)
    try:
        _, access_token, refresh_token = auth_service.refresh(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
def logout(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    auth_service = AuthService(db)
    authorization = request.headers.get("Authorization", "")
    access_token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else None
    auth_service.logout(payload.refresh_token, access_token)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=CurrentUserResponse)
def current_user(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role_id=user.role_id,
        role_name=user.role.name,
        is_verified=user.is_verified,
        is_active=user.is_active,
        last_login=user.last_login,
    )
