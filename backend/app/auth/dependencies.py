from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.role import Role
from app.models.user import User
from app.services.redis_service import RedisService
from app.utils.security import decode_token

security = HTTPBearer(auto_error=False)
EMPLOYEE_PORTAL_ROLES = {"employee", "manager", "hr", "payroll administrator", "security analyst"}
ADMINISTRATOR_PORTAL_ROLE = "sentinelai administrator"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = credentials.credentials
    if RedisService().get_value(f"blacklist:{token}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")

    request.state.user_id = user.id
    request.state.user_email = user.email
    request.state.user_role_id = user.role_id
    return user


def get_workspace_user(user: User = Depends(get_current_user)) -> User:
    if not user.role or user.role.name.casefold() not in EMPLOYEE_PORTAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def get_administrator_user(user: User = Depends(get_current_user)) -> User:
    if not user.role or user.role.name.casefold() != ADMINISTRATOR_PORTAL_ROLE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def _normalize_role_name(name: str) -> str:
    normalized = name.replace(" ", "").lower()
    return {"securityanalyst": "analyst"}.get(normalized, normalized)


def require_roles(*allowed_roles: str):
    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        allowed_names = {_normalize_role_name(name) for name in allowed_roles}
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if not role or _normalize_role_name(role.name) not in allowed_names:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
