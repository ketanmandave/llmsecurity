from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role_id": role_id,
        "jti": str(uuid4()),
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "jti": str(uuid4()),
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "iat": now,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
