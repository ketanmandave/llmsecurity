from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    app_name: Mapped[str] = mapped_column(String(100), nullable=False, default="SentinelAI")
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="dark")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="en")
    session_timeout: Mapped[int] = mapped_column(default=30, nullable=False)
