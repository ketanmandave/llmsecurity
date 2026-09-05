"""Tests for deployment liveness and dependency readiness endpoints."""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class HealthApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_liveness_does_not_require_dependencies(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_readiness_is_healthy_when_dependencies_respond(self) -> None:
        with (
            patch("app.api.health._database_ready", new=AsyncMock(return_value=True)),
            patch("app.api.health._redis_ready", new=AsyncMock(return_value=True)),
        ):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_readiness_fails_when_database_is_unavailable(self) -> None:
        with (
            patch("app.api.health._database_ready", new=AsyncMock(return_value=False)),
            patch("app.api.health._redis_ready", new=AsyncMock(return_value=True)),
        ):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "unavailable")


if __name__ == "__main__":
    unittest.main()
