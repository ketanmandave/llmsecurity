from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from app.gateway.risk.assessment import RecommendedAction, RiskSeverity


class PolicyDecisionType(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class PolicyDecision:
    decision: PolicyDecisionType
    reason: str
    explanation: str
    policy_name: str
    policy_version: str
    risk_score: int
    risk_severity: RiskSeverity
    recommended_action: RecommendedAction
    user_role: str
    user_id: str
    conversation_id: str
    request_id: str
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
