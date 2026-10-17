from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogService:
    def __init__(self, db: Session):
        self.db = db

    def list_logs(self, skip: int = 0, limit: int = 50) -> list[AuditLog]:
        return self.db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    def create_log(self, action: str, status: str, user_id: str | None = None, ip_address: str | None = None, details: str | None = None) -> AuditLog:
        log = AuditLog(user_id=user_id, action=action, status=status, ip_address=ip_address, details=details)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
