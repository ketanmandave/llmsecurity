from datetime import datetime
from typing import Any

from sqlalchemy import case, cast, desc, func, or_, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.models.security_event import SecurityEvent
from app.models.user import User
from app.schemas.dashboard import (
    DetectorAnalyticsOut, DetectorCount, InvestigationOut, OutcomeAnalyticsOut,
    RiskAnalyticsOut, RiskPoint, SecurityIntentAnalyticsOut, SecurityIntentCount, TimelineEventOut, UserActivityOut,
)


class DashboardAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def timeline(self, *, user_id: str | None = None, conversation_id: str | None = None,
                 request_id: str | None = None, severity: str | None = None,
                 policy_decision: str | None = None, authorization_decision: str | None = None,
                 start_time: datetime | None = None, end_time: datetime | None = None,
                 search: str | None = None, skip: int = 0, limit: int = 50) -> list[TimelineEventOut]:
        query = self._filtered_events(user_id=user_id, conversation_id=conversation_id, request_id=request_id,
                                      severity=severity, policy_decision=policy_decision,
                                      authorization_decision=authorization_decision, start_time=start_time,
                                      end_time=end_time, search=search)
        events = query.order_by(desc(SecurityEvent.request_timestamp), desc(SecurityEvent.id)).offset(skip).limit(limit).all()
        return [TimelineEventOut(event_id=e.id, request_id=e.request_id, conversation_id=e.conversation_id,
                                 timestamp=e.request_timestamp, user_id=e.user_id, user_role=e.user_role,
                                 risk_score=e.risk_score, risk_severity=e.risk_severity,
                                 policy_decision=e.policy_decision, authorization_decision=e.authorization_decision,
                                 outcome=e.outcome) for e in events]

    def investigation(self, identifier: str) -> InvestigationOut | None:
        event = self.db.query(SecurityEvent).filter(or_(SecurityEvent.id == identifier, SecurityEvent.request_id == identifier)).first()
        return InvestigationOut.model_validate(event) if event else None

    def outcomes(self) -> OutcomeAnalyticsOut:
        warned = or_(SecurityEvent.outcome == "review", SecurityEvent.policy_decision.in_(("WARN", "ESCALATE")))
        total, allowed, blocked, warned_count = self.db.query(
            func.count(SecurityEvent.id),
            func.sum(case((SecurityEvent.outcome == "allowed", 1), else_=0)),
            func.sum(case((SecurityEvent.outcome.in_(("blocked", "denied")), 1), else_=0)),
            func.sum(case((warned, 1), else_=0)),
        ).one()
        policies = self.db.query(SecurityEvent.policy_decision, func.count(SecurityEvent.id)).filter(SecurityEvent.policy_decision.is_not(None)).group_by(SecurityEvent.policy_decision).all()
        total = int(total or 0)
        values = {"allowed": int(allowed or 0), "blocked": int(blocked or 0), "warned_or_reviewed": int(warned_count or 0)}
        return OutcomeAnalyticsOut(total_requests=total, allowed_requests=values["allowed"], blocked_requests=values["blocked"], warned_or_reviewed_requests=values["warned_or_reviewed"], percentages={key: round(value * 100 / total, 2) if total else 0 for key, value in values.items()}, policy_distribution={str(key): int(value) for key, value in policies})

    def risk(self) -> RiskAnalyticsOut:
        average = self.db.query(func.avg(SecurityEvent.risk_score)).scalar()
        distribution = self.db.query(SecurityEvent.risk_severity, func.count(SecurityEvent.id)).filter(SecurityEvent.risk_severity.is_not(None)).group_by(SecurityEvent.risk_severity).all()
        high = self.db.query(func.count(SecurityEvent.id)).filter(SecurityEvent.risk_severity.in_(("HIGH", "CRITICAL"))).scalar()
        bucket = func.date_trunc("hour", SecurityEvent.request_timestamp)
        trend_rows = self.db.query(bucket, func.avg(SecurityEvent.risk_score), func.sum(case((SecurityEvent.risk_severity.in_(("HIGH", "CRITICAL")), 1), else_=0))).filter(SecurityEvent.risk_score.is_not(None)).group_by(bucket).order_by(bucket).limit(168).all()
        return RiskAnalyticsOut(average_risk_score=round(float(average or 0), 2), severity_distribution={str(key): int(value) for key, value in distribution}, high_risk_requests=int(high or 0), trend=[RiskPoint(timestamp=timestamp, average_score=round(float(score or 0), 2), high_risk_count=int(count or 0)) for timestamp, score, count in trend_rows])

    def users(self, limit: int = 50) -> list[UserActivityOut]:
        threat_rows = self._threat_user_counts()
        rows = self.db.query(SecurityEvent.user_id, User.name, User.email, func.count(SecurityEvent.id), func.sum(case((SecurityEvent.outcome == "allowed", 1), else_=0)), func.sum(case((SecurityEvent.outcome.in_(("blocked", "denied")), 1), else_=0)), func.avg(SecurityEvent.risk_score), func.max(SecurityEvent.request_timestamp)).join(User, User.id == SecurityEvent.user_id).group_by(SecurityEvent.user_id, User.name, User.email).order_by(desc(func.max(SecurityEvent.request_timestamp))).limit(limit).all()
        return [UserActivityOut(user_id=user_id, user_name=name, user_email=email, request_count=int(count), threat_count=threat_rows.get(user_id, 0), allowed_count=int(allowed or 0), blocked_count=int(blocked or 0), average_risk_score=round(float(average or 0), 2), last_activity=last_activity) for user_id, name, email, count, allowed, blocked, average, last_activity in rows]

    def detectors(self) -> DetectorAnalyticsOut:
        prompt_rows = func.jsonb_array_elements(cast(SecurityEvent.detector_results, JSONB)).table_valued("value").alias("prompt_detectors")
        value = cast(prompt_rows.c.value, JSONB)
        rows = self.db.query(value).select_from(SecurityEvent).join(prompt_rows, true()).filter(SecurityEvent.detector_results.is_not(None)).all()
        counts: dict[str, DetectorCount] = {}
        for (raw,) in rows:
            self._add_detector(counts, raw)
        response_events = self.db.query(SecurityEvent.response_assessment).filter(SecurityEvent.response_assessment.is_not(None)).all()
        for (assessment,) in response_events:
            for item in (assessment or {}).get("detector_breakdown", []):
                self._add_detector(counts, (item or {}).get("result", item))
        total = sum(item.count for item in counts.values())
        detected = sum(item.non_safe_count for item in counts.values())
        return DetectorAnalyticsOut(total_observations=total, detected_observations=detected, detectors=sorted(counts.values(), key=lambda item: item.detector_name))

    def semantic_intents(self) -> SecurityIntentAnalyticsOut:
        """Extract and aggregate security_intent values from detector metadata."""
        prompt_rows = func.jsonb_array_elements(cast(SecurityEvent.detector_results, JSONB)).table_valued("value").alias("prompt_detectors")
        value = cast(prompt_rows.c.value, JSONB)
        rows = self.db.query(value).select_from(SecurityEvent).join(prompt_rows, true()).filter(SecurityEvent.detector_results.is_not(None)).all()

        counts: dict[str, SecurityIntentCount] = {}
        for (raw,) in rows:
            self._add_security_intent(counts, raw)

        # Also check response assessment for semantic intents if present
        response_events = self.db.query(SecurityEvent.response_assessment).filter(SecurityEvent.response_assessment.is_not(None)).all()
        for (assessment,) in response_events:
            for item in (assessment or {}).get("detector_breakdown", []):
                self._add_security_intent(counts, (item or {}).get("result", item))

        total = sum(item.count for item in counts.values())
        dangerous = sum(item.dangerous_count for item in counts.values())
        return SecurityIntentAnalyticsOut(total_observations=total, dangerous_observations=dangerous, intents=sorted(counts.values(), key=lambda item: item.security_intent))

    def _add_security_intent(self, counts: dict[str, SecurityIntentCount], raw: Any) -> None:
        """Extract security_intent from detector result metadata and aggregate."""
        if not isinstance(raw, dict):
            return

        # Try to get security_intent from metadata
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            return

        security_intent = metadata.get("security_intent")
        if not security_intent:
            return

        intent_name = str(security_intent)
        status = str(raw.get("status", "SAFE"))

        item = counts.setdefault(intent_name, SecurityIntentCount(security_intent=intent_name, count=0, dangerous_count=0))
        item.count += 1
        if status != "SAFE":
            item.dangerous_count += 1


    def _add_detector(self, counts: dict[str, DetectorCount], raw: Any) -> None:
        if not isinstance(raw, dict) or not raw.get("detector_name"):
            return
        name = str(raw["detector_name"])
        status = str(raw.get("status", "SAFE"))
        severity = str(raw.get("severity", "LOW"))
        item = counts.setdefault(name, DetectorCount(detector_name=name, count=0, non_safe_count=0, severity_counts={}))
        item.count += 1
        if status != "SAFE": item.non_safe_count += 1
        item.severity_counts[severity] = item.severity_counts.get(severity, 0) + 1

    def _threat_user_counts(self) -> dict[str, int]:
        detector_rows = func.jsonb_array_elements(cast(SecurityEvent.detector_results, JSONB)).table_valued("value").alias("d")
        detector_value = cast(detector_rows.c.value, JSONB)
        rows = self.db.query(SecurityEvent.user_id, func.count()).select_from(SecurityEvent).join(detector_rows, true()).filter(SecurityEvent.detector_results.is_not(None), detector_value["status"].astext != "SAFE").group_by(SecurityEvent.user_id).all()
        return {user_id: int(count) for user_id, count in rows if count > 0}

    def _filtered_events(self, **filters: Any):
        query = self.db.query(SecurityEvent)
        for field in ("user_id", "conversation_id", "request_id"):
            if filters[field]: query = query.filter(getattr(SecurityEvent, field) == filters[field])
        mappings = {"severity": SecurityEvent.risk_severity, "policy_decision": SecurityEvent.policy_decision, "authorization_decision": SecurityEvent.authorization_decision}
        for key, column in mappings.items():
            if filters[key]: query = query.filter(column == filters[key])
        if filters["start_time"]: query = query.filter(SecurityEvent.request_timestamp >= filters["start_time"])
        if filters["end_time"]: query = query.filter(SecurityEvent.request_timestamp <= filters["end_time"])
        if filters["search"]:
            term = f"%{filters['search']}%"
            query = query.filter(or_(SecurityEvent.request_id.ilike(term), SecurityEvent.conversation_id.ilike(term), SecurityEvent.user_id.ilike(term)))
        return query
