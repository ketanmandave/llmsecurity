from app.gateway.detectors.result import DetectorResult, DetectorStatus
from app.gateway.risk.assessment import DetectorBreakdown, RecommendedAction, RiskAssessment, RiskSeverity
from app.gateway.risk.config import RECOMMENDED_ACTIONS, SEVERITY_THRESHOLDS, profile_for


class RiskIntelligenceEngine:
    """Aggregates detector evidence; it never enforces the resulting recommendation.

    Each triggered detector contributes ``score * confidence/100 * weight``.
    The overall score normalizes those contributions against the maximum possible
    weighted contribution from the triggered detectors, keeping scores in 0-100.
    Overall confidence is a weighted evidence confidence, not an arithmetic
    average of detector scores.
    """

    def assess(self, detector_results: list[DetectorResult]) -> RiskAssessment:
        breakdown = [self._breakdown(result) for result in detector_results]
        triggered = [item for item in breakdown if item.status is not DetectorStatus.SAFE]
        total_weight = sum(item.weight for item in triggered)
        total_contribution = sum(item.weighted_contribution for item in triggered)

        overall_score = round((total_contribution / (100 * total_weight)) * 100) if total_weight else 0
        confidence_weight = sum(item.weight * item.score for item in triggered)
        overall_confidence = round(
            sum(item.confidence * item.weight * item.score for item in triggered) / confidence_weight,
        ) if confidence_weight else 100
        severity = self._severity_for(overall_score)
        action = RecommendedAction(RECOMMENDED_ACTIONS[severity.value])
        highest = max(triggered, key=lambda item: item.weighted_contribution, default=None)
        summary = self._summary(len(triggered), len(breakdown), highest, severity)

        return RiskAssessment(
            overall_score=overall_score,
            overall_confidence=overall_confidence,
            overall_severity=severity,
            recommended_action=action,
            summary=summary,
            highest_detector=highest.detector_name if highest else None,
            highest_detector_score=highest.score if highest else 0,
            highest_detector_confidence=highest.confidence if highest else 0,
            triggered_detector_count=len(triggered),
            total_detector_count=len(breakdown),
            detector_breakdown=breakdown,
            metadata={"aggregation": "weighted_score_confidence_evidence"},
        )

    @staticmethod
    def _breakdown(result: DetectorResult) -> DetectorBreakdown:
        profile = profile_for(result.detector_name)
        contribution = round(result.score * (result.confidence / 100) * profile.weight, 2)
        return DetectorBreakdown(
            detector_id=profile.detector_id,
            detector_name=result.detector_name,
            category=profile.category,
            status=result.status,
            score=result.score,
            confidence=result.confidence,
            weight=profile.weight,
            weighted_contribution=contribution,
            reason=result.reason,
            matched_patterns=result.matched_patterns,
            severity=RiskIntelligenceEngine._severity_for(result.score),
            metadata=result.metadata,
            timestamp=result.timestamp,
        )

    @staticmethod
    def _severity_for(score: int) -> RiskSeverity:
        for severity, threshold in SEVERITY_THRESHOLDS:
            if score >= threshold:
                return RiskSeverity(severity)
        return RiskSeverity.LOW

    @staticmethod
    def _summary(triggered_count: int, total_count: int, highest: DetectorBreakdown | None, severity: RiskSeverity) -> str:
        if not highest:
            return f"No detector observations were triggered across {total_count} detectors."
        return (
            f"{triggered_count} of {total_count} detectors produced observations; "
            f"{highest.detector_name} contributed the most evidence. Overall severity is {severity.value}."
        )
