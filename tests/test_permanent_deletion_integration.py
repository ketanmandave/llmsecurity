"""Database test for irreversible document and vector deletion."""

import hashlib
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from sqlalchemy import delete, func, select

from app.config import EMBEDDING_DIMENSION, Settings
from app.database import AsyncSessionFactory, engine
from app.models import (
    AccessRole,
    Chunk,
    Classification,
    Document,
    DocumentRole,
    DocumentStatus,
    SecurityFinding,
    SecurityStatus,
    Severity,
)
from app.services.document_service import activate_document, permanently_delete_document


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 to run PostgreSQL integration tests",
)
class PermanentDeletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        await engine.dispose()

    async def test_removes_document_vector_acl_finding_and_pdf(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            upload_root = Path(directory)
            stored_directory = upload_root / "documents"
            stored_directory.mkdir()
            document_id = uuid.uuid4()
            stored_path = stored_directory / f"{document_id}.pdf"
            stored_path.write_bytes(b"%PDF-1.7\ntest")

            async with AsyncSessionFactory() as session:
                document = Document(
                    id=document_id,
                    name="Permanent deletion test",
                    original_filename="deletion-test.pdf",
                    storage_key=f"documents/{document_id}.pdf",
                    mime_type="application/pdf",
                    checksum_sha256=hashlib.sha256(b"delete-test").hexdigest(),
                    size_bytes=14,
                    classification=Classification.INTERNAL,
                    status=DocumentStatus.ACTIVE,
                    uploaded_by="integration-test",
                    roles=[DocumentRole(role=AccessRole.EMPLOYEE)],
                    chunks=[
                        Chunk(
                            content="This vector must be deleted",
                            page_number=1,
                            chunk_index=0,
                            content_hash=hashlib.sha256(b"chunk").hexdigest(),
                            embedding=[0.0] * EMBEDDING_DIMENSION,
                            security_status=SecurityStatus.APPROVED,
                        )
                    ],
                )
                session.add(document)
                await session.flush()
                session.add(
                    SecurityFinding(
                        document_id=document_id,
                        category="test_finding",
                        severity=Severity.LOW,
                        description="Deletion cascade test",
                    )
                )
                await session.commit()
                await session.refresh(document, attribute_names=["roles"])

                file_deleted = await permanently_delete_document(
                    session,
                    document,
                    Settings(upload_directory=upload_root),
                )

            self.assertTrue(file_deleted)
            self.assertFalse(stored_path.exists())
            async with AsyncSessionFactory() as verification_session:
                for model, identifier in (
                    (Document, Document.id),
                    (DocumentRole, DocumentRole.document_id),
                    (Chunk, Chunk.document_id),
                    (SecurityFinding, SecurityFinding.document_id),
                ):
                    count = await verification_session.scalar(
                        select(func.count()).select_from(model).where(identifier == document_id)
                    )
                    self.assertEqual(count, 0, model.__name__)

    async def test_inactive_document_reuses_existing_vectors_when_activated(self) -> None:
        document_id = uuid.uuid4()
        async with AsyncSessionFactory() as session:
            document = Document(
                id=document_id,
                name="Activation test",
                original_filename="activation-test.pdf",
                storage_key=f"documents/{document_id}.pdf",
                mime_type="application/pdf",
                checksum_sha256=hashlib.sha256(b"activation-test").hexdigest(),
                size_bytes=100,
                classification=Classification.INTERNAL,
                status=DocumentStatus.INACTIVE,
                uploaded_by="integration-test",
                roles=[DocumentRole(role=AccessRole.EMPLOYEE)],
                chunks=[
                    Chunk(
                        content="Reusable indexed content",
                        page_number=1,
                        chunk_index=0,
                        content_hash=hashlib.sha256(b"reusable-chunk").hexdigest(),
                        embedding=[0.0] * EMBEDDING_DIMENSION,
                        security_status=SecurityStatus.APPROVED,
                    )
                ],
            )
            session.add(document)
            await session.commit()

            activated, reprocessing = await activate_document(session, document)
            await session.commit()

            self.assertEqual(activated.status, DocumentStatus.ACTIVE)
            self.assertFalse(reprocessing)
            chunk_count = await session.scalar(
                select(func.count()).select_from(Chunk).where(
                    Chunk.document_id == document_id
                )
            )
            self.assertEqual(chunk_count, 1)
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.commit()


if __name__ == "__main__":
    unittest.main()
