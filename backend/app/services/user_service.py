from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    def list_users(self) -> list[User]:
        return self.repository.list()

    def get_user(self, user_id: str) -> User | None:
        return self.repository.get_by_id(user_id)

    def create_user(self, name: str, email: str, password: str, role_id: int) -> User:
        if self.repository.get_by_email(email):
            raise ValueError("Email already registered")
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("Role not found")
        user = User(name=name, email=email, password_hash=hash_password(password), role_id=role.id)
        return self.repository.create(user)

    def update_user(self, user: User, name: str | None = None, email: str | None = None) -> User:
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        return self.repository.update(user)

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        from app.utils.security import verify_password

        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        return self.repository.update(user)

    def toggle_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        if is_active:
            user.is_verified = True
        return self.repository.update(user)

    def assign_role(self, user: User, role_id: int) -> User:
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("Role not found")
        user.role_id = role.id
        return self.repository.update(user)
