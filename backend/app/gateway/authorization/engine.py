import json
import logging
import time

from app.gateway.authorization.decision import AuthorizationDecision, AuthorizationStatus
from app.gateway.authorization.rules import AuthorizationRule
from app.gateway.context import RequestContext

logger = logging.getLogger("sentinelai.gateway.authorization")


class AuthorizationEvaluator:
    def __init__(self, rule: AuthorizationRule | None = None) -> None:
        self.rule = rule or AuthorizationRule()

    def evaluate(self, context: RequestContext) -> AuthorizationDecision:
        started = time.perf_counter()
        self._log(context, "authorization_started", started)
        match = self.rule.evaluate(context)
        self._log(context, "authorization_rule_matched", started, resource=match.resource, action=match.action, decision=match.status.value, matched_rule=match.matched_rule)
        reason = "Authorization granted." if match.status is AuthorizationStatus.ALLOW else (
            "This request requires additional authorization." if match.status is AuthorizationStatus.REVIEW else "This request is not authorized under your current access permissions."
        )
        decision = AuthorizationDecision(
            status=match.status, user_id=context.user_id, role=context.role, resource=match.resource,
            action=match.action, reason=reason, matched_rule=match.matched_rule,
            request_id=context.request_id, conversation_id=context.conversation_id,
        )
        self._log(context, "authorization_completed", started, resource=match.resource, action=match.action, decision=decision.status.value, matched_rule=match.matched_rule)
        if decision.status is AuthorizationStatus.DENY:
            self._log(context, "authorization_denied", started, level=logging.WARNING, resource=match.resource, action=match.action, decision=decision.status.value, matched_rule=match.matched_rule)
        return decision

    @staticmethod
    def _log(context: RequestContext, event: str, started: float, level: int = logging.INFO, **fields: object) -> None:
        logger.log(level, json.dumps({"event": event, "request_id": context.request_id, "conversation_id": context.conversation_id, "user_id": context.user_id, "role": context.role, "processing_time_ms": round((time.perf_counter() - started) * 1000, 2), **fields}))
