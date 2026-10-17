from sqlalchemy.orm import Session

from app.models.setting import Setting


class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> Setting:
        settings = self.db.query(Setting).first()
        if not settings:
            settings = Setting()
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update_settings(self, settings: Setting, app_name: str, theme: str, language: str, session_timeout: int) -> Setting:
        settings.app_name = app_name
        settings.theme = theme
        settings.language = language
        settings.session_timeout = session_timeout
        self.db.commit()
        self.db.refresh(settings)
        return settings
