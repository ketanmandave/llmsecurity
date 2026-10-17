from datetime import datetime, timezone

from app.gateway.context import RequestContext
from app.gateway.detectors.result import DetectorResult, DetectorStatus
from app.gateway.risk.assessment import RecommendedAction, RiskSeverity
from app.gateway.risk.engine import RiskIntelligenceEngine
from app.gateway.stages import RiskEngine


def _result(name: str, status: DetectorStatus, score: int, confidence: int) -> DetectorResult:
    return DetectorResult(name, status, score, confidence, "test observation")


def test_weighted_assessment_preserves_breakdown_and_uses_confidence() -> None:
    results = [
        _result("PromptInjectionDetector", DetectorStatus.DANGEROUS, 80, 90),
        _result("JailbreakDetector", DetectorStatus.SAFE, 0, 100),
        _result("SensitiveKeywordDetector", DetectorStatus.WARNING, 50, 85),
    ]

    assessment = RiskIntelligenceEngine().assess(results)

    assert assessment.total_detector_count == 3
    assert assessment.triggered_detector_count == 2
    assert assessment.highest_detector == "PromptInjectionDetector"
    assert assessment.overall_score == 57
    assert assessment.overall_confidence == 88
    assert assessment.overall_severity is RiskSeverity.HIGH
    assert assessment.recommended_action is RecommendedAction.ESCALATE
    assert len(assessment.detector_breakdown) == 3
    assert assessment.detector_breakdown[0].weight == 1.0
    assert assessment.detector_breakdown[0].weighted_contribution == 72.0


def test_unknown_future_detector_uses_default_profile() -> None:
    assessment = RiskIntelligenceEngine().assess([_result("FutureDetector", DetectorStatus.WARNING, 30, 80)])

    assert assessment.detector_breakdown[0].weight == 1.0
    assert assessment.detector_breakdown[0].detector_id == "DETECTOR_FUTUREDETECTOR"
    assert assessment.overall_score == 24


def test_risk_stage_attaches_assessment_without_changing_detector_results() -> None:
    results = [_result("SensitiveKeywordDetector", DetectorStatus.WARNING, 50, 85)]
    context = RequestContext(
        request_id="risk-request",
        conversation_id="risk-conversation",
        user_id="risk-user",
        role="employee",
        prompt="unchanged",
        timestamp=datetime.now(timezone.utc),
        provider="openai",
        detector_results=results,
    )

    returned = RiskEngine().evaluate(context)

    assert returned is context
    assert context.detector_results == results
    assert context.risk_assessment is not None
    assert context.risk_assessment.recommended_action is RecommendedAction.WARN
