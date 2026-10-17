from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.gateway.detectors.result import DetectorResult
from app.gateway.risk.assessment import RiskAssessment
from app.gateway.policy.decision import PolicyDecision
from app.gateway.response_security.assessment import ResponseAssessment
from app.gateway.authorization.decision import AuthorizationDecision


@dataclass
class RequestContext:
    request_id: str
    conversation_id: str
    user_id: str
    role: str
    prompt: str
    timestamp: datetime
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)
    detector_results: list[DetectorResult] = field(default_factory=list)
    risk_assessment: RiskAssessment | None = None
    policy_decision: PolicyDecision | None = None
    response_assessment: ResponseAssessment | None = None
    authorization_decision: AuthorizationDecision | None = None
