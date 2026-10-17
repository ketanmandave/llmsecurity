from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SecurityEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    conversation_id: str | None = None
    user_id: str
    user_role: str
    request_timestamp: datetime
    completed_at: datetime
    prompt: str
    authorization_decision: str | None = None
    authorization_reason: str | None = None
    detector_results: list[dict[str, Any]] | None = None
    risk_score: int | None = None
    risk_severity: str | None = None
    policy_decision: str | None = None
    outcome: str
    provider: str | None = None
    provider_called: bool
    provider_status_code: int | None = None
    response_assessment: dict[str, Any] | None = None
    response_outcome: str | None = None
    latency_ms: float | None = None
    metadata_json: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
