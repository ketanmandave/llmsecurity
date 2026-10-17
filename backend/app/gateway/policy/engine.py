from app.gateway.context import RequestContext
from app.gateway.detectors.result import DetectorStatus
from app.gateway.policy.config import (
    BLOCK_ON_CRITICAL_DETECTOR_EVIDENCE,
    CRITICAL_EVIDENCE_POLICY_NAME,
    POLICY_NAME,
    POLICY_VERSION,
    ROLE_DECISION_OVERRIDES,
    SEVERITY_DECISIONS,
)
from app.gateway.policy.decision import PolicyDecision, PolicyDecisionType
from app.gateway.risk.assessment import RiskSeverity


class PolicyEvaluator:
    """Produces final decisions from risk evidence without inspecting prompt content."""

    def evaluate(self, context: RequestContext) -> PolicyDecision:
        assessment = context.risk_assessment
        if assessment is None:
            raise ValueError("Policy evaluation requires a risk assessment")

        critical_evidence = any(
            item.severity is RiskSeverity.CRITICAL and item.status is not DetectorStatus.SAFE
            for item in assessment.detector_breakdown
        )
        if BLOCK_ON_CRITICAL_DETECTOR_EVIDENCE and critical_evidence:
            decision = PolicyDecisionType.BLOCK
            policy_name = CRITICAL_EVIDENCE_POLICY_NAME
            reason = "Critical detector evidence requires blocking."
        else:
            decision = ROLE_DECISION_OVERRIDES.get(context.role, {}).get(
                assessment.overall_severity,
                SEVERITY_DECISIONS[assessment.overall_severity],
            )
            policy_name = POLICY_NAME
            reason = "Decision follows the configured risk severity policy."

        return PolicyDecision(
            decision=decision,
            reason=reason,
            explanation=(
                f"Risk severity {assessment.overall_severity.value} maps to {decision.value} "
                "under the active policy configuration."
            ),
            policy_name=policy_name,
            policy_version=POLICY_VERSION,
            risk_score=assessment.overall_score,
            risk_severity=assessment.overall_severity,
            recommended_action=assessment.recommended_action,
            user_role=context.role,
            user_id=context.user_id,
            conversation_id=context.conversation_id,
            request_id=context.request_id,
            metadata={"triggered_detector_count": assessment.triggered_detector_count},
        )
