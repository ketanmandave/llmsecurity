from typing import Any

from sqlalchemy import case, cast, func, or_, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.models.security_event import SecurityEvent
from app.schemas.dashboard import DashboardMetricsOut, RecentSecurityActivity


class DashboardMetricsService:
    RECENT_ACTIVITY_LIMIT = 10

    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self) -> DashboardMetricsOut:
        total, allowed, blocked, warned, average_risk = self._request_metrics()
        return DashboardMetricsOut(
            total_requests=int(total or 0),
            allowed_requests=int(allowed or 0),
            blocked_requests=int(blocked or 0),
            warned_requests=int(warned or 0),
            threat_counts=self._threat_counts(),
            average_risk_score=round(float(average_risk or 0), 2),
            recent_security_activity=self._recent_activity(),
        )

    def _request_metrics(self) -> tuple[Any, Any, Any, Any, Any]:
        warned_or_reviewed = or_(
            SecurityEvent.outcome == "review",
            SecurityEvent.policy_decision.in_(("WARN", "ESCALATE")),
        )
        return self.db.query(
            func.count(SecurityEvent.id),
            func.coalesce(func.sum(case((SecurityEvent.outcome == "allowed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((SecurityEvent.outcome.in_(("blocked", "denied")), 1), else_=0)), 0),
            func.coalesce(func.sum(case((warned_or_reviewed, 1), else_=0)), 0),
            func.coalesce(func.avg(SecurityEvent.risk_score), 0),
        ).one()

    def _threat_counts(self) -> dict[str, int]:
        detector_rows = func.jsonb_array_elements(cast(SecurityEvent.detector_results, JSONB)).table_valued("value").alias("detector_rows")
        detector_value = cast(detector_rows.c.value, JSONB)
        detector_name = detector_value["detector_name"].astext
        rows = (
            self.db.query(detector_name.label("detector_name"), func.count().label("count"))
            .select_from(SecurityEvent)
            .join(detector_rows, true())
            .filter(SecurityEvent.detector_results.is_not(None), detector_value["status"].astext != "SAFE")
            .group_by(detector_name)
            .order_by(detector_name)
            .all()
        )
        return {name: count for name, count in rows}

    def _recent_activity(self) -> list[RecentSecurityActivity]:
        events = (
            self.db.query(SecurityEvent)
            .order_by(SecurityEvent.request_timestamp.desc(), SecurityEvent.id.desc())
            .limit(self.RECENT_ACTIVITY_LIMIT)
            .all()
        )
        return [
            RecentSecurityActivity(
                event_id=event.id,
                request_id=event.request_id,
                timestamp=event.request_timestamp,
                user_id=event.user_id,
                user_role=event.user_role,
                risk_score=event.risk_score,
                risk_severity=event.risk_severity,
                policy_decision=event.policy_decision,
                authorization_decision=event.authorization_decision,
                outcome=event.outcome,
            )
            for event in events
        ]
