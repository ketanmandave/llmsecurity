from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role_permission import RolePermission


class PermissionService:
    def __init__(self, db: Session):
        self.db = db

    def list_permissions(self) -> list[Permission]:
        return self.db.query(Permission).all()

    def ensure_defaults(self) -> None:
        defaults = [
            ("users.read", "Read users"),
            ("users.create", "Create users"),
            ("users.update", "Update users"),
            ("users.delete", "Delete users"),
            ("audit.read", "Read audit logs"),
            ("settings.update", "Update settings"),
            ("dashboard.view", "View dashboard"),
            ("detectors.read", "Read detectors"),
        ]
        for name, description in defaults:
            if not self.db.query(Permission).filter(Permission.name == name).first():
                self.db.add(Permission(name=name, description=description))
        self.db.commit()

    def assign_permission(self, role_id: int, permission_name: str) -> None:
        permission = self.db.query(Permission).filter(Permission.name == permission_name).first()
        if not permission:
            raise ValueError("Permission not found")
        existing = self.db.query(RolePermission).filter(RolePermission.role_id == role_id, RolePermission.permission_id == permission.id).first()
        if not existing:
            self.db.add(RolePermission(role_id=role_id, permission_id=permission.id))
            self.db.commit()
