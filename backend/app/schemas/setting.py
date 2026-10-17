from pydantic import BaseModel, Field


class SettingBase(BaseModel):
    app_name: str = Field(default="SentinelAI")
    theme: str = Field(default="dark")
    language: str = Field(default="en")
    session_timeout: int = Field(default=30, ge=5, le=1440)


class SettingOut(SettingBase):
    id: int

    class Config:
        from_attributes = True
