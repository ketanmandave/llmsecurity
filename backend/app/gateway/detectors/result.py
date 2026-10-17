from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DetectorStatus(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGEROUS = "DANGEROUS"


@dataclass(frozen=True)
class DetectorResult:
    detector_name: str
    status: DetectorStatus
    score: int
    confidence: int
    reason: str
    matched_patterns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
