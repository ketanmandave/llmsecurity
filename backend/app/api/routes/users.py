from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_administrator_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import PasswordChange, UserCreate, UserOut, UserRoleUpdate, UserStatusUpdate, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> list[UserOut]:
    service = UserService(db)
    users = service.list_users()
    return users


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> UserOut:
    service = UserService(db)
    try:
        created_user = service.create_user(payload.name, payload.email, payload.password, payload.role_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return created_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> UserOut:
    service = UserService(db)
    record = service.get_user(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return record


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> UserOut:
    service = UserService(db)
    record = service.get_user(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = service.update_user(record, name=payload.name, email=payload.email)
    return updated


@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(user_id: str, payload: UserStatusUpdate, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> UserOut:
    if user.id == user_id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot deactivate their own account")
    service = UserService(db)
    record = service.get_user(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return service.toggle_active(record, payload.is_active)


@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(user_id: str, payload: UserRoleUpdate, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> UserOut:
    if user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot change their own role")
    service = UserService(db)
    record = service.get_user(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        return service.assign_role(record, payload.role_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{user_id}/change-password")
def change_password(user_id: str, payload: PasswordChange, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> dict[str, str]:
    service = UserService(db)
    record = service.get_user(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    service.change_password(record, payload.current_password, payload.new_password)
    return {"message": "Password changed successfully"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> None:
    service = UserService(db)
    record = service.get_user(user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(record)
    db.commit()
