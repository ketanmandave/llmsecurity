import json
import logging
from sqlalchemy.orm import Session

from app.gateway.context import RequestContext
from app.gateway.prompt_security_pipeline import PromptSecurityPipeline
from app.gateway.policy.engine import PolicyEvaluator
from app.gateway.risk.engine import RiskIntelligenceEngine
from app.gateway.authorization.engine import AuthorizationEvaluator
from app.services.security_event_service import SecurityEventService

logger = logging.getLogger("sentinelai.gateway.risk")


class PromptPipeline:
    def __init__(self, pipeline: PromptSecurityPipeline | None = None) -> None:
        self.pipeline = pipeline or PromptSecurityPipeline()

    def process(self, context: RequestContext) -> RequestContext:
        return self.pipeline.process(context)


class AuthorizationEngine:
    def __init__(self, evaluator: AuthorizationEvaluator | None = None) -> None:
        self.evaluator = evaluator or AuthorizationEvaluator()

    def authorize(self, context: RequestContext) -> RequestContext:
        context.authorization_decision = self.evaluator.evaluate(context)
        return context


class RiskEngine:
    def __init__(self, engine: RiskIntelligenceEngine | None = None) -> None:
        self.engine = engine or RiskIntelligenceEngine()

    def evaluate(self, context: RequestContext) -> RequestContext:
        context.risk_assessment = self.engine.assess(context.detector_results)
        assessment = context.risk_assessment
        logger.info(json.dumps({
            "event": "risk_assessment_completed",
            "request_id": context.request_id,
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "detectors_executed": assessment.total_detector_count,
            "highest_detector": assessment.highest_detector,
            "overall_score": assessment.overall_score,
            "overall_confidence": assessment.overall_confidence,
            "overall_severity": assessment.overall_severity.value,
            "recommended_action": assessment.recommended_action.value,
        }))
        return context


class PolicyEngine:
    def __init__(self, evaluator: PolicyEvaluator | None = None) -> None:
        self.evaluator = evaluator or PolicyEvaluator()

    def evaluate(self, context: RequestContext) -> RequestContext:
        context.policy_decision = self.evaluator.evaluate(context)
        decision = context.policy_decision
        logger.info(json.dumps({
            "event": "policy_decision_completed",
            "request_id": context.request_id,
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "decision": decision.decision.value,
            "policy_name": decision.policy_name,
            "risk_score": decision.risk_score,
            "risk_severity": decision.risk_severity.value,
            "user_role": decision.user_role,
        }))
        return context


class ResponsePipeline:
    def process(self, context: RequestContext, response: str) -> str:
        # TODO: Add response-security processing in a future phase.
        return response


class AuditLogger:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def record(self, context: RequestContext, event: str) -> RequestContext:
        # Stage events remain in application logs; one complete event is persisted at the end.
        return context

    def persist(self, context: RequestContext, **kwargs) -> None:
        if self.db is not None:
            SecurityEventService(self.db).create_from_context(context, **kwargs)
