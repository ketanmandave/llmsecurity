from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict


class RecentSecurityActivity(BaseModel):
    event_id: str
    request_id: str
    timestamp: datetime
    user_id: str
    user_role: str
    risk_score: int | None = None
    risk_severity: str | None = None
    policy_decision: str | None = None
    authorization_decision: str | None = None
    outcome: str


class DashboardMetricsOut(BaseModel):
    total_requests: int
    allowed_requests: int
    blocked_requests: int
    warned_requests: int
    threat_counts: dict[str, int]
    average_risk_score: float
    recent_security_activity: list[RecentSecurityActivity]


class TimelineEventOut(RecentSecurityActivity):
    conversation_id: str | None = None


class DetectorCount(BaseModel):
    detector_name: str
    count: int
    non_safe_count: int
    severity_counts: dict[str, int] = {}


class SecurityIntentCount(BaseModel):
    security_intent: str
    count: int
    dangerous_count: int


class SecurityIntentAnalyticsOut(BaseModel):
    total_observations: int
    dangerous_observations: int
    intents: list[SecurityIntentCount]



class DetectorAnalyticsOut(BaseModel):
    total_observations: int
    detected_observations: int
    detectors: list[DetectorCount]


class RiskPoint(BaseModel):
    timestamp: datetime
    average_score: float
    high_risk_count: int


class RiskAnalyticsOut(BaseModel):
    average_risk_score: float
    severity_distribution: dict[str, int]
    high_risk_requests: int
    trend: list[RiskPoint]


class OutcomeAnalyticsOut(BaseModel):
    total_requests: int
    allowed_requests: int
    blocked_requests: int
    warned_or_reviewed_requests: int
    percentages: dict[str, float]
    policy_distribution: dict[str, int]


class UserActivityOut(BaseModel):
    user_id: str
    user_name: str | None = None
    user_email: str | None = None
    request_count: int
    threat_count: int
    allowed_count: int
    blocked_count: int
    average_risk_score: float
    last_activity: datetime


class InvestigationOut(BaseModel):
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
