from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.gateway.detectors.result import DetectorStatus


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class DetectorBreakdown:
    detector_id: str
    detector_name: str
    category: str
    status: DetectorStatus
    score: int
    confidence: int
    weight: float
    weighted_contribution: float
    reason: str
    matched_patterns: list[str]
    severity: RiskSeverity
    metadata: dict[str, Any]
    timestamp: datetime


@dataclass(frozen=True)
class RiskAssessment:
    overall_score: int
    overall_confidence: int
    overall_severity: RiskSeverity
    recommended_action: RecommendedAction
    summary: str
    highest_detector: str | None
    highest_detector_score: int
    highest_detector_confidence: int
    triggered_detector_count: int
    total_detector_count: int
    detector_breakdown: list[DetectorBreakdown] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
