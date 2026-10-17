from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.gateway.detectors.result import DetectorStatus
from app.gateway.risk.assessment import RiskSeverity


@dataclass(frozen=True)
class ResponseDetectionResult:
    detector_id: str
    detector_name: str
    category: str
    status: DetectorStatus
    score: int
    confidence: int
    severity: RiskSeverity
    reason: str
    matched_patterns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ResponseDetectorBreakdown:
    result: ResponseDetectionResult
    weight: float
    weighted_contribution: float


@dataclass(frozen=True)
class ResponseAssessment:
    overall_score: int
    overall_confidence: int
    overall_severity: RiskSeverity
    highest_detector: str | None
    detector_breakdown: list[ResponseDetectorBreakdown] = field(default_factory=list)
    summary: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
