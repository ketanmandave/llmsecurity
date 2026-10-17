from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_administrator_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogOut
from app.services.audit_log_service import AuditLogService

router = APIRouter()


@router.get("", response_model=list[AuditLogOut])
def list_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_administrator_user),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    return AuditLogService(db).list_logs(skip=skip, limit=limit)
