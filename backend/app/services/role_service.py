from sqlalchemy.orm import Session

from app.models.role import Role


class RoleService:
    def __init__(self, db: Session):
        self.db = db

    def list_roles(self) -> list[Role]:
        return self.db.query(Role).all()

    def create_role(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role
