"""HTTP tests for the integrated administrator dashboard."""

import unittest

from fastapi.testclient import TestClient

from app.auth.jwt import Principal
from app.auth.permissions import require_admin
from app.main import app
from app.models.enums import AccessRole


class AdminDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_dashboard_and_assets_are_served_with_security_headers(self) -> None:
        response = self.client.get("/admin")
        stylesheet = self.client.get("/admin/assets/styles.css")
        script = self.client.get("/admin/assets/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Document control center", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("app.js?v=20260905-4", response.text)
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(script.status_code, 200)
        self.assertIn("Delete permanently", script.text)
        self.assertIn("Activate document", script.text)
        self.assertIn("/activate", script.text)
        self.assertIn("/permanent", script.text)

    def test_upload_configuration_requires_admin_and_returns_valid_choices(self) -> None:
        unauthorized = self.client.get("/v1/documents/config")
        self.assertEqual(unauthorized.status_code, 401)

        app.dependency_overrides[require_admin] = lambda: Principal(
            "admin-1", frozenset({AccessRole.ADMIN})
        )
        response = self.client.get("/v1/documents/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["allowed_roles"],
            ["admin", "hr", "manager", "employee"],
        )
        self.assertIn("restricted", response.json()["classifications"])
        self.assertEqual(response.json()["accepted_file_types"], ["application/pdf"])


if __name__ == "__main__":
    unittest.main()
