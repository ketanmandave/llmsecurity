from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_administrator_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.setting import SettingOut
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("", response_model=SettingOut)
def get_settings(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> SettingOut:
    return SettingsService(db).get_settings()


@router.put("", response_model=SettingOut)
def update_settings(payload: SettingOut, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> SettingOut:
    service = SettingsService(db)
    settings = service.get_settings()
    return service.update_settings(settings, payload.app_name, payload.theme, payload.language, payload.session_timeout)
