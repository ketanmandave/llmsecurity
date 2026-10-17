from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database.init_db import init_db
from app.database.session import SessionLocal
from app.main import app
from app.models.conversation import Conversation, Message
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.services.dashboard_metrics_service import DashboardMetricsService
from app.services.redis_service import RedisService


def _test_conversation() -> tuple[str, str]:
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "employee@company.com").first()
        conversation = Conversation(user_session=user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation.id, user.id
    finally:
        db.close()


def _event(
    conversation_id: str,
    user_id: str,
    timestamp: datetime,
    *,
    outcome: str,
    policy_decision: str,
    risk_score: int,
    detectors: list[dict],
) -> SecurityEvent:
    return SecurityEvent(
        request_id=str(uuid4()),
        conversation_id=conversation_id,
        user_id=user_id,
        user_role="employee",
        request_timestamp=timestamp,
        completed_at=timestamp,
        prompt="dashboard metric test",
        detector_results=detectors,
        risk_score=risk_score,
        risk_severity="HIGH" if risk_score >= 50 else "MEDIUM",
        policy_decision=policy_decision,
        outcome=outcome,
        provider="openai",
        provider_called=outcome == "allowed",
    )


def _cleanup(conversation_id: str) -> None:
    db = SessionLocal()
    try:
        db.query(SecurityEvent).filter(SecurityEvent.conversation_id == conversation_id).delete()
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            db.delete(conversation)
        db.commit()
    finally:
        db.close()


def test_metrics_are_calculated_from_persisted_security_events() -> None:
    conversation_id, user_id = _test_conversation()
    try:
        db = SessionLocal()
        try:
            baseline = DashboardMetricsService(db).get_metrics()
            base_time = datetime.now(timezone.utc) + timedelta(days=1)
            events = [
                _event(conversation_id, user_id, base_time, outcome="allowed", policy_decision="ALLOW", risk_score=10, detectors=[]),
                _event(conversation_id, user_id, base_time + timedelta(seconds=1), outcome="blocked", policy_decision="BLOCK", risk_score=90, detectors=[{"detector_name": "PromptInjectionDetector", "status": "DANGEROUS"}]),
                _event(conversation_id, user_id, base_time + timedelta(seconds=2), outcome="allowed", policy_decision="WARN", risk_score=40, detectors=[{"detector_name": "JailbreakDetector", "status": "DANGEROUS"}]),
                _event(conversation_id, user_id, base_time + timedelta(seconds=3), outcome="review", policy_decision="ALLOW", risk_score=20, detectors=[]),
            ]
            db.add_all(events)
            db.commit()

            metrics = DashboardMetricsService(db).get_metrics()
            assert metrics.total_requests == baseline.total_requests + 4
            assert metrics.allowed_requests == baseline.allowed_requests + 2
            assert metrics.blocked_requests == baseline.blocked_requests + 1
            assert metrics.warned_requests == baseline.warned_requests + 2
            assert metrics.threat_counts.get("PromptInjectionDetector", 0) == baseline.threat_counts.get("PromptInjectionDetector", 0) + 1
            assert metrics.threat_counts.get("JailbreakDetector", 0) == baseline.threat_counts.get("JailbreakDetector", 0) + 1
            expected_average = ((baseline.average_risk_score * baseline.total_requests) + 160) / (baseline.total_requests + 4)
            assert metrics.average_risk_score == round(expected_average, 2)
            assert [item.request_id for item in metrics.recent_security_activity[:4]] == [event.request_id for event in reversed(events)]
        finally:
            db.close()
    finally:
        _cleanup(conversation_id)


def test_metrics_endpoint_is_administrator_only() -> None:
    init_db()
    RedisService().delete_value("ratelimit:/api/v1/auth/login:testclient")
    with TestClient(app) as client:
        assert client.get("/api/v1/dashboard/metrics").status_code == 401

        employee_login = client.post("/api/v1/auth/login", json={"email": "employee@company.com", "password": "employee123", "login_as": "Employee", "portal": "employee"})
        employee_headers = {"Authorization": f"Bearer {employee_login.json()['access_token']}"}
        assert client.get("/api/v1/dashboard/metrics", headers=employee_headers).status_code == 403

        admin_login = client.post("/api/v1/auth/login", json={"email": "admin@sentinelai.com", "password": "sentinelai123", "portal": "administrator"})
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        response = client.get("/api/v1/dashboard/metrics", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"total_requests", "allowed_requests", "blocked_requests", "warned_requests", "threat_counts", "average_risk_score", "recent_security_activity"}


def test_empty_metric_values_are_safe() -> None:
    service = DashboardMetricsService(SessionLocal())
    try:
        service._request_metrics = lambda: (0, 0, 0, 0, 0)  # type: ignore[method-assign]
        service._threat_counts = lambda: {}  # type: ignore[method-assign]
        service._recent_activity = lambda: []  # type: ignore[method-assign]
        assert service.get_metrics().model_dump() == {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "warned_requests": 0,
            "threat_counts": {},
            "average_risk_score": 0.0,
            "recent_security_activity": [],
        }
    finally:
        service.db.close()
