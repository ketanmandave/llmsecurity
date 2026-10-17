from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AuthorizationStatus(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


@dataclass(frozen=True)
class AuthorizationDecision:
    status: AuthorizationStatus
    user_id: str
    role: str
    resource: str
    action: str
    reason: str
    matched_rule: str | None
    request_id: str
    conversation_id: str
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
