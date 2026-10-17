import re
from abc import ABC, abstractmethod

from app.gateway.detectors.result import DetectorStatus
from app.gateway.response_security.assessment import ResponseDetectionResult
from app.gateway.response_security.config import RESPONSE_DETECTOR_CONFIGS, ResponseDetectorConfig

_REGISTRY: list[type["BaseResponseDetector"]] = []


def register_response_detector(detector: type["BaseResponseDetector"]) -> type["BaseResponseDetector"]:
    _REGISTRY.append(detector)
    return detector


def registered_detectors() -> list[type["BaseResponseDetector"]]:
    return list(_REGISTRY)


class BaseResponseDetector(ABC):
    @abstractmethod
    def detect(self, response_text: str) -> ResponseDetectionResult:
        """Analyze a response without modifying it."""


class ConfiguredRegexResponseDetector(BaseResponseDetector):
    config_name: str

    @property
    def config(self) -> ResponseDetectorConfig:
        return RESPONSE_DETECTOR_CONFIGS[self.config_name]

    def detect(self, response_text: str) -> ResponseDetectionResult:
        matches = [name for name, pattern in self.config.patterns.items() if re.search(pattern, response_text, re.IGNORECASE)]
        if matches:
            return ResponseDetectionResult(
                detector_id=self.config.detector_id,
                detector_name=self.__class__.__name__,
                category=self.config.category,
                status=self.config.status,
                score=self.config.score,
                confidence=self.config.confidence,
                severity=self.config.severity,
                reason=f"Matched {self.config.category.lower()} pattern.",
                matched_patterns=matches,
            )
        return ResponseDetectionResult(
            detector_id=self.config.detector_id,
            detector_name=self.__class__.__name__,
            category=self.config.category,
            status=DetectorStatus.SAFE,
            score=0,
            confidence=100,
            severity=self.config.severity.__class__.LOW,
            reason=f"No {self.config.category.lower()} pattern matched.",
        )
