from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_administrator_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.role import RoleCreate, RoleOut
from app.services.role_service import RoleService

router = APIRouter()


@router.get("", response_model=list[RoleOut])
def list_roles(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> list[RoleOut]:
    return RoleService(db).list_roles()


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> RoleOut:
    try:
        return RoleService(db).create_role(payload.name, payload.description)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
