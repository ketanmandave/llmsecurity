"""JWT verification and verified-role authorization tests."""

import unittest
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException

from app.auth.jwt import Principal, decode_access_token
from app.auth.permissions import has_any_role
from app.config import Settings
from app.models.enums import AccessRole


TEST_SECRET = "test-secret-that-is-long-enough-for-hs256"


class JwtRoleExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            jwt_secret_key=TEST_SECRET,
            jwt_issuer="test-backend",
            jwt_audience="test-rag",
            jwt_leeway_seconds=0,
        )

    def make_token(self, **overrides: object) -> str:
        now = datetime.now(UTC)
        claims: dict[str, object] = {
            "sub": "employee-123",
            "roles": ["hr", "employee"],
            "iss": "test-backend",
            "aud": "test-rag",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        claims.update(overrides)
        return jwt.encode(claims, TEST_SECRET, algorithm="HS256")

    def test_extracts_user_and_known_roles(self) -> None:
        principal = decode_access_token(self.make_token(), self.settings)

        self.assertEqual(principal.user_id, "employee-123")
        self.assertEqual(
            principal.roles,
            frozenset({AccessRole.HR, AccessRole.EMPLOYEE}),
        )

    def test_rejects_expired_token(self) -> None:
        token = self.make_token(exp=datetime.now(UTC) - timedelta(seconds=1))
        with self.assertRaises(HTTPException) as raised:
            decode_access_token(token, self.settings)
        self.assertEqual(raised.exception.status_code, 401)

    def test_rejects_wrong_signature(self) -> None:
        token = jwt.encode(
            {
                "sub": "employee-123",
                "roles": ["hr"],
                "iss": "test-backend",
                "aud": "test-rag",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            "forged-secret-that-is-long-enough-for-hs256",
            algorithm="HS256",
        )
        with self.assertRaises(HTTPException):
            decode_access_token(token, self.settings)

    def test_rejects_wrong_audience(self) -> None:
        with self.assertRaises(HTTPException):
            decode_access_token(self.make_token(aud="different-service"), self.settings)

    def test_rejects_missing_required_claim(self) -> None:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": "employee-123",
                "roles": ["hr"],
                "iss": "test-backend",
                "aud": "test-rag",
                "exp": now + timedelta(minutes=5),
            },
            TEST_SECRET,
            algorithm="HS256",
        )
        with self.assertRaises(HTTPException):
            decode_access_token(token, self.settings)

    def test_rejects_unknown_role(self) -> None:
        with self.assertRaises(HTTPException):
            decode_access_token(self.make_token(roles=["super_admin"]), self.settings)

    def test_role_authorization_uses_verified_role_set(self) -> None:
        principal = Principal(
            user_id="employee-123",
            roles=frozenset({AccessRole.HR}),
        )
        self.assertTrue(has_any_role(principal, {AccessRole.HR, AccessRole.MANAGER}))
        self.assertFalse(has_any_role(principal, {AccessRole.ADMIN}))


if __name__ == "__main__":
    unittest.main()
