import re
from dataclasses import asdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.gateway.context import RequestContext
from app.models.security_event import SecurityEvent


SECRET_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b(?:bearer\s+)[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "[REDACTED_JWT]"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE), "[REDACTED_PASSWORD]"),
    (re.compile(r"\b(?:API_KEY|SECRET_KEY|DATABASE_URL)\s*=\s*\S+", re.IGNORECASE), "[REDACTED_SECRET]"),
)


def redact_audit_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted[:10000]


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _detector_results(context: RequestContext) -> list[dict[str, Any]]:
    return [_json_value(asdict(result)) for result in context.detector_results]


def _response_assessment(context: RequestContext) -> dict[str, Any] | None:
    assessment = context.response_assessment
    if assessment is None:
        return None
    return _json_value(asdict(assessment))


class SecurityEventService:
    def __init__(self, db: Session):
        self.db = db

    def create_from_context(
        self,
        context: RequestContext,
        *,
        outcome: str,
        provider_called: bool,
        latency_ms: float,
        provider_status_code: int | None = None,
        response_outcome: str | None = None,
        error: Exception | None = None,
    ) -> SecurityEvent:
        authorization = context.authorization_decision
        risk = context.risk_assessment
        policy = context.policy_decision
        event = SecurityEvent(
            request_id=context.request_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            user_role=context.role,
            request_timestamp=context.timestamp,
            prompt=redact_audit_text(context.prompt) or "",
            authorization_decision=authorization.status.value if authorization else None,
            authorization_reason=redact_audit_text(authorization.reason) if authorization else None,
            detector_results=_detector_results(context),
            risk_score=risk.overall_score if risk else None,
            risk_severity=risk.overall_severity.value if risk else None,
            policy_decision=policy.decision.value if policy else None,
            outcome=outcome,
            provider=context.provider,
            provider_called=provider_called,
            provider_status_code=provider_status_code,
            response_assessment=_response_assessment(context),
            response_outcome=response_outcome,
            latency_ms=latency_ms,
            metadata_json=_json_value(context.metadata),
            error_type=type(error).__name__ if error else None,
            error_message=redact_audit_text(str(error)) if error else None,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(
        self,
        *,
        conversation_id: str | None = None,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        severity: str | None = None,
        policy_decision: str | None = None,
        authorization_decision: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[SecurityEvent]:
        query = self.db.query(SecurityEvent)
        if conversation_id:
            query = query.filter(SecurityEvent.conversation_id == conversation_id)
        if user_id:
            query = query.filter(SecurityEvent.user_id == user_id)
        if start_time:
            query = query.filter(SecurityEvent.request_timestamp >= start_time)
        if end_time:
            query = query.filter(SecurityEvent.request_timestamp <= end_time)
        if severity:
            query = query.filter(SecurityEvent.risk_severity == severity)
        if policy_decision:
            query = query.filter(SecurityEvent.policy_decision == policy_decision)
        if authorization_decision:
            query = query.filter(SecurityEvent.authorization_decision == authorization_decision)
        return query.order_by(SecurityEvent.request_timestamp.desc()).offset(skip).limit(limit).all()
