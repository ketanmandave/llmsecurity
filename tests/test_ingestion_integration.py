"""Optional PostgreSQL integration test for the complete ingestion transaction."""

import hashlib
import os
import tempfile
import unittest
import uuid
from pathlib import Path

import pymupdf
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import EMBEDDING_DIMENSION, Settings
from app.database import AsyncSessionFactory, engine
from app.ingestion.pipeline import process_document
from app.models import (
    AccessRole,
    Chunk,
    Classification,
    Document,
    DocumentRole,
    DocumentStatus,
)


class FakeEmbedder:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * EMBEDDING_DIMENSION for _ in texts]


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 to run PostgreSQL integration tests",
)
class IngestionDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        await engine.dispose()

    async def test_ingestion_activates_document_and_preserves_acl(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            document_id = uuid.uuid4()
            document_directory = root / "documents"
            document_directory.mkdir()
            pdf_path = document_directory / f"{document_id}.pdf"

            pdf = pymupdf.open()
            page = pdf.new_page()
            page.insert_text(
                (72, 72),
                "HR policy contact: hr@example.com. Employees receive twenty leave days.",
            )
            pdf.save(pdf_path)
            pdf.close()
            raw_bytes = pdf_path.read_bytes()

            async with AsyncSessionFactory() as session:
                transaction = await session.begin()
                try:
                    document = Document(
                        id=document_id,
                        name="Integration Test Policy",
                        original_filename="policy.pdf",
                        storage_key=f"documents/{document_id}.pdf",
                        mime_type="application/pdf",
                        checksum_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                        size_bytes=len(raw_bytes),
                        classification=Classification.INTERNAL,
                        status=DocumentStatus.PROCESSING,
                        uploaded_by="integration-test",
                        roles=[DocumentRole(role=AccessRole.HR)],
                    )
                    session.add(document)
                    await session.flush()

                    result_status = await process_document(
                        session,
                        document_id,
                        Settings(upload_directory=root),
                        FakeEmbedder(),
                    )

                    loaded = (
                        await session.execute(
                            select(Document)
                            .options(selectinload(Document.roles))
                            .where(Document.id == document_id)
                        )
                    ).scalar_one()
                    chunks = list(
                        (
                            await session.execute(
                                select(Chunk).where(Chunk.document_id == document_id)
                            )
                        ).scalars()
                    )

                    self.assertEqual(result_status, DocumentStatus.ACTIVE)
                    self.assertEqual(loaded.status, DocumentStatus.ACTIVE)
                    self.assertEqual([entry.role for entry in loaded.roles], [AccessRole.HR])
                    self.assertGreater(len(chunks), 0)
                    self.assertIn("[EMAIL_REDACTED]", chunks[0].content)
                    self.assertEqual(len(chunks[0].embedding), EMBEDDING_DIMENSION)
                finally:
                    await transaction.rollback()


if __name__ == "__main__":
    unittest.main()
