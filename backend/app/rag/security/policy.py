"""Helpers for combining security-policy decisions."""

from app.rag.models.enums import PolicyDecision


_DECISION_PRIORITY = {
    PolicyDecision.ALLOW: 0,
    PolicyDecision.MODIFY: 1,
    PolicyDecision.QUARANTINE: 2,
    PolicyDecision.BLOCK: 3,
}


def combine_decisions(*decisions: PolicyDecision) -> PolicyDecision:
    """Return the strictest decision supplied by the security layers."""

    if not decisions:
        return PolicyDecision.ALLOW
    return max(decisions, key=_DECISION_PRIORITY.__getitem__)
