from datetime import datetime, timezone

from app.gateway.context import RequestContext
from app.gateway.detectors.result import DetectorStatus
from app.gateway.response_security.engine import ResponseSecurityEngine


def _context() -> RequestContext:
    return RequestContext(
        request_id="response-request",
        conversation_id="response-conversation",
        user_id="response-user",
        role="employee",
        prompt="unchanged prompt",
        timestamp=datetime.now(timezone.utc),
        provider="openai",
    )


def _analyze(response: str) -> RequestContext:
    context = _context()
    assert ResponseSecurityEngine().analyze(context, response) == response
    assert context.response_assessment is not None
    return context


def test_safe_response_is_preserved_and_assessed_safe() -> None:
    context = _analyze("The quarterly meeting starts at 10 AM.")

    assert context.response_assessment.overall_score == 0
    assert all(item.result.status is DetectorStatus.SAFE for item in context.response_assessment.detector_breakdown)


def test_api_key_response_is_detected_without_modification() -> None:
    response = "Use sk-abcdefghijklmnopqrstuvwxyz123456 for this demonstration."
    context = _analyze(response)

    assert context.response_assessment.highest_detector == "SensitiveDataLeakDetector"
    leak = next(item.result for item in context.response_assessment.detector_breakdown if item.result.detector_name == "SensitiveDataLeakDetector")
    assert "openai_api_key" in leak.matched_patterns


def test_email_response_is_detected() -> None:
    context = _analyze("Contact analyst@example.com for assistance.")

    pii = next(item.result for item in context.response_assessment.detector_breakdown if item.result.detector_name == "PIIDetector")
    assert pii.status is DetectorStatus.WARNING
    assert "email" in pii.matched_patterns


def test_toxic_response_is_detected() -> None:
    context = _analyze("I will kill you.")

    toxicity = next(item.result for item in context.response_assessment.detector_breakdown if item.result.detector_name == "ToxicityDetector")
    assert toxicity.status is DetectorStatus.DANGEROUS


def test_uncertainty_response_is_detected_with_low_confidence() -> None:
    context = _analyze("I think this may be the correct answer.")

    marker = next(item.result for item in context.response_assessment.detector_breakdown if item.result.detector_name == "HallucinationMarkerDetector")
    assert marker.status is DetectorStatus.WARNING
    assert marker.confidence == 40


def test_multiple_response_observations_aggregate() -> None:
    context = _analyze("Email analyst@example.com and use sk-abcdefghijklmnopqrstuvwxyz123456. I think maybe this works.")

    assessment = context.response_assessment
    assert len([item for item in assessment.detector_breakdown if item.result.status is not DetectorStatus.SAFE]) == 3
    assert assessment.overall_score > 0
    assert assessment.highest_detector == "SensitiveDataLeakDetector"
