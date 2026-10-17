from app.gateway.policy.decision import PolicyDecisionType
from app.gateway.risk.assessment import RiskSeverity

POLICY_NAME = "Risk Severity Policy"
POLICY_VERSION = "1.0"
CRITICAL_EVIDENCE_POLICY_NAME = "Critical Detector Evidence Policy"

SEVERITY_DECISIONS = {
    RiskSeverity.LOW: PolicyDecisionType.ALLOW,
    RiskSeverity.MEDIUM: PolicyDecisionType.WARN,
    RiskSeverity.HIGH: PolicyDecisionType.ESCALATE,
    RiskSeverity.CRITICAL: PolicyDecisionType.BLOCK,
}

# Future role-aware policies can add overrides without changing evaluator code.
ROLE_DECISION_OVERRIDES: dict[str, dict[RiskSeverity, PolicyDecisionType]] = {}
BLOCK_ON_CRITICAL_DETECTOR_EVIDENCE = True
