"""HTTP-level tests for bearer-token identity extraction."""

import unittest
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


class CurrentPrincipalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.settings = get_settings()

    def token(self) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": "hr-007",
                "roles": ["hr", "employee"],
                "iss": self.settings.jwt_issuer,
                "aud": self.settings.jwt_audience,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )

    def test_me_returns_roles_from_verified_token(self) -> None:
        response = self.client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {self.token()}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_id": "hr-007", "roles": ["employee", "hr"]},
        )

    def test_me_rejects_missing_token(self) -> None:
        response = self.client.get("/v1/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")


if __name__ == "__main__":
    unittest.main()
