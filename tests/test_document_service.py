"""Unit tests for document upload validation and role parsing."""

import io
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import Settings
from app.models.enums import AccessRole
from app.services.document_service import parse_allowed_roles, store_pdf


class ParseAllowedRolesTests(unittest.TestCase):
    def test_accepts_known_unique_roles(self) -> None:
        self.assertEqual(
            parse_allowed_roles('["hr", "manager"]'),
            [AccessRole.HR, AccessRole.MANAGER],
        )

    def test_accepts_comma_separated_roles(self) -> None:
        self.assertEqual(
            parse_allowed_roles("employee,hr,manager"),
            [AccessRole.EMPLOYEE, AccessRole.HR, AccessRole.MANAGER],
        )

    def test_rejects_unknown_role(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            parse_allowed_roles('["superuser"]')
        self.assertEqual(raised.exception.status_code, 422)

    def test_rejects_duplicate_roles(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            parse_allowed_roles('["hr", "hr"]')
        self.assertEqual(raised.exception.status_code, 422)


class StorePdfTests(unittest.IsolatedAsyncioTestCase):
    async def test_stores_valid_pdf_under_generated_name(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            document_id = uuid.uuid4()
            settings = Settings(upload_directory=Path(directory))
            upload = UploadFile(
                filename="employee-policy.pdf",
                file=io.BytesIO(b"%PDF-1.7\nexample"),
            )

            stored = await store_pdf(upload, document_id, settings)

            self.assertEqual(stored.original_filename, "employee-policy.pdf")
            self.assertEqual(stored.storage_key, f"documents/{document_id}.pdf")
            self.assertTrue(stored.absolute_path.exists())
            self.assertEqual(stored.absolute_path.read_bytes(), b"%PDF-1.7\nexample")

    async def test_rejects_non_pdf_content(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            settings = Settings(upload_directory=Path(directory))
            upload = UploadFile(
                filename="fake.pdf",
                file=io.BytesIO(b"not a pdf"),
            )

            with self.assertRaises(HTTPException) as raised:
                await store_pdf(upload, uuid.uuid4(), settings)

            self.assertEqual(raised.exception.status_code, 415)


if __name__ == "__main__":
    unittest.main()
