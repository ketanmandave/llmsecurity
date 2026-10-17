from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_administrator_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.security_event import SecurityEventOut
from app.services.security_event_service import SecurityEventService

router = APIRouter()


@router.get("", response_model=list[SecurityEventOut])
def list_security_events(
    conversation_id: str | None = None,
    user_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    severity: str | None = None,
    policy_decision: str | None = None,
    authorization_decision: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_administrator_user),
    db: Session = Depends(get_db),
) -> list[SecurityEventOut]:
    return SecurityEventService(db).list_events(
        conversation_id=conversation_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        severity=severity,
        policy_decision=policy_decision,
        authorization_decision=authorization_decision,
        skip=skip,
        limit=limit,
    )
