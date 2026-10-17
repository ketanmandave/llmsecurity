from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_conversation_timestamp", "conversation_id", "event_timestamp"),
        Index("ix_security_events_user_timestamp", "user_id", "event_timestamp"),
        Index("ix_security_events_policy_decision", "policy_decision"),
        Index("ix_security_events_authorization_decision", "authorization_decision"),
        Index("ix_security_events_risk_severity", "risk_severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    user_role: Mapped[str] = mapped_column(String(100), nullable=False)
    # Preserve the established timestamp column names in already initialized databases.
    request_timestamp: Mapped[datetime] = mapped_column("event_timestamp", DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column("created_at", DateTime, default=datetime.utcnow, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    authorization_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    authorization_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detector_results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    policy_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # ``llm_reached`` is the established column name in older initialized databases.
    provider_called: Mapped[bool] = mapped_column("llm_reached", nullable=False, default=False)
    provider_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    conversation = relationship("Conversation", back_populates="security_events")
    user = relationship("User", back_populates="security_events")
