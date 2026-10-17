from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_administrator_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardMetricsOut, DetectorAnalyticsOut, InvestigationOut, OutcomeAnalyticsOut, RiskAnalyticsOut, SecurityIntentAnalyticsOut, TimelineEventOut, UserActivityOut
from app.services.dashboard_analytics_service import DashboardAnalyticsService
from app.services.dashboard_metrics_service import DashboardMetricsService

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetricsOut)
def get_dashboard_metrics(
    user: User = Depends(get_administrator_user),
    db: Session = Depends(get_db),
) -> DashboardMetricsOut:
    return DashboardMetricsService(db).get_metrics()


@router.get("/timeline", response_model=list[TimelineEventOut])
def get_timeline(user_id: str | None = None, conversation_id: str | None = None, request_id: str | None = None,
                 severity: str | None = None, policy_decision: str | None = None, authorization_decision: str | None = None,
                 start_time: datetime | None = None, end_time: datetime | None = None, search: str | None = None,
                 skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                 user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> list[TimelineEventOut]:
    return DashboardAnalyticsService(db).timeline(user_id=user_id, conversation_id=conversation_id, request_id=request_id, severity=severity, policy_decision=policy_decision, authorization_decision=authorization_decision, start_time=start_time, end_time=end_time, search=search, skip=skip, limit=limit)


@router.get("/detectors", response_model=DetectorAnalyticsOut)
def get_detector_analytics(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> DetectorAnalyticsOut:
    return DashboardAnalyticsService(db).detectors()


@router.get("/semantic-intents", response_model=SecurityIntentAnalyticsOut)
def get_semantic_intents(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> SecurityIntentAnalyticsOut:
    return DashboardAnalyticsService(db).semantic_intents()


@router.get("/risk", response_model=RiskAnalyticsOut)
def get_risk_analytics(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> RiskAnalyticsOut:
    return DashboardAnalyticsService(db).risk()


@router.get("/outcomes", response_model=OutcomeAnalyticsOut)
def get_outcome_analytics(user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> OutcomeAnalyticsOut:
    return DashboardAnalyticsService(db).outcomes()


@router.get("/users", response_model=list[UserActivityOut])
def get_user_activity(limit: int = Query(50, ge=1, le=100), user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> list[UserActivityOut]:
    return DashboardAnalyticsService(db).users(limit)


@router.get("/investigations/{identifier}", response_model=InvestigationOut)
def get_investigation(identifier: str, user: User = Depends(get_administrator_user), db: Session = Depends(get_db)) -> InvestigationOut:
    investigation = DashboardAnalyticsService(db).investigation(identifier)
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security event not found")
    return investigation
