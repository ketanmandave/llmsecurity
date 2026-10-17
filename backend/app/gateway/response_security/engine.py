import json
import logging

from app.gateway.context import RequestContext
from app.gateway.detectors.result import DetectorStatus
from app.gateway.response_security.assessment import ResponseAssessment, ResponseDetectorBreakdown
from app.gateway.response_security.config import DEFAULT_RESPONSE_DETECTOR_WEIGHT, RESPONSE_DETECTOR_CONFIGS, RESPONSE_SEVERITY_THRESHOLDS
from app.gateway.response_security.detectors import discover_response_detectors
from app.gateway.response_security.detectors.base import BaseResponseDetector
from app.gateway.risk.assessment import RiskSeverity

logger = logging.getLogger("sentinelai.gateway.response_security")


class ResponseSecurityEngine:
    """Orchestrates response detectors and returns the exact original response."""

    def __init__(self, detectors: list[BaseResponseDetector] | None = None) -> None:
        self.detectors = detectors or [detector() for detector in discover_response_detectors()]

    def analyze(self, context: RequestContext, response_text: str) -> str:
        results = []
        for detector in self.detectors:
            result = detector.detect(response_text)
            results.append(result)
            logger.info(json.dumps({
                "event": "response_detector_completed",
                "request_id": context.request_id,
                "conversation_id": context.conversation_id,
                "user_id": context.user_id,
                "detector": result.detector_name,
                "status": result.status.value,
            }))

        context.response_assessment = self._assess(results)
        assessment = context.response_assessment
        logger.info(json.dumps({
            "event": "response_security_completed",
            "request_id": context.request_id,
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "overall_score": assessment.overall_score,
            "overall_severity": assessment.overall_severity.value,
        }))
        return response_text

    @staticmethod
    def _assess(results):
        breakdown = []
        for result in results:
            config = RESPONSE_DETECTOR_CONFIGS.get(result.detector_name)
            weight = config.weight if config else DEFAULT_RESPONSE_DETECTOR_WEIGHT
            contribution = round(result.score * (result.confidence / 100) * weight, 2)
            breakdown.append(ResponseDetectorBreakdown(result, weight, contribution))
        triggered = [item for item in breakdown if item.result.status is not DetectorStatus.SAFE]
        total_weight = sum(item.weight for item in triggered)
        total_contribution = sum(item.weighted_contribution for item in triggered)
        overall_score = round(total_contribution / total_weight) if total_weight else 0
        confidence_weight = sum(item.result.score * item.weight for item in triggered)
        overall_confidence = round(sum(item.result.confidence * item.result.score * item.weight for item in triggered) / confidence_weight) if confidence_weight else 100
        severity = ResponseSecurityEngine._severity_for(overall_score)
        highest = max(triggered, key=lambda item: item.weighted_contribution, default=None)
        summary = "No response-security observations were triggered." if not highest else f"{highest.result.detector_name} contributed the most response-security evidence."
        return ResponseAssessment(overall_score, overall_confidence, severity, highest.result.detector_name if highest else None, breakdown, summary)

    @staticmethod
    def _severity_for(score: int) -> RiskSeverity:
        for severity, threshold in RESPONSE_SEVERITY_THRESHOLDS:
            if score >= threshold:
                return RiskSeverity(severity)
        return RiskSeverity.LOW
