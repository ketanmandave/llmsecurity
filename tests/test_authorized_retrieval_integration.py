"""PostgreSQL tests proving authorization is enforced during vector retrieval."""

import hashlib
import os
import unittest
import uuid

from app.config import EMBEDDING_DIMENSION
from app.database import AsyncSessionFactory, engine
from app.models import (
    AccessRole,
    Chunk,
    Classification,
    Document,
    DocumentRole,
    DocumentStatus,
    SecurityStatus,
)
from app.retrieval.retriever import (
    DocumentScopeError,
    retrieve_authorized_chunks,
    validate_authorized_document_scope,
)


def vector(first: float, second: float) -> list[float]:
    value = [0.0] * EMBEDDING_DIMENSION
    value[0] = first
    value[1] = second
    return value


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 to run PostgreSQL integration tests",
)
class AuthorizedRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        await engine.dispose()

    async def test_each_role_receives_only_authorized_chunks(self) -> None:
        async with AsyncSessionFactory() as session:
            transaction = await session.begin()
            try:
                def add_document(
                    name: str,
                    roles: list[AccessRole],
                    content: str,
                    embedding: list[float],
                    document_status: DocumentStatus = DocumentStatus.ACTIVE,
                ) -> uuid.UUID:
                    document_id = uuid.uuid4()
                    session.add(
                        Document(
                            id=document_id,
                            name=name,
                            original_filename=f"{document_id}.pdf",
                            storage_key=f"documents/{document_id}.pdf",
                            mime_type="application/pdf",
                            checksum_sha256=hashlib.sha256(name.encode()).hexdigest(),
                            size_bytes=100,
                            classification=Classification.INTERNAL,
                            status=document_status,
                            uploaded_by="integration-test",
                            roles=[DocumentRole(role=role) for role in roles],
                            chunks=[
                                Chunk(
                                    content=content,
                                    page_number=1,
                                    chunk_index=0,
                                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                                    embedding=embedding,
                                    security_status=SecurityStatus.APPROVED,
                                )
                            ],
                        )
                    )
                    return document_id

                hr_document = add_document(
                    "HR Salary Policy",
                    [AccessRole.HR],
                    "Confidential HR salary policy",
                    vector(1.0, 0.0),
                )
                manager_document = add_document(
                    "Manager Budget",
                    [AccessRole.MANAGER],
                    "Confidential manager budget",
                    vector(1.0, 0.0),
                )
                common_document = add_document(
                    "Employee Leave Policy",
                    [AccessRole.HR, AccessRole.MANAGER, AccessRole.EMPLOYEE],
                    "General employee leave policy",
                    vector(0.9, 0.1),
                )
                inactive_document = add_document(
                    "Inactive HR Policy",
                    [AccessRole.HR],
                    "Old inactive HR policy",
                    vector(1.0, 0.0),
                    DocumentStatus.INACTIVE,
                )
                await session.flush()

                hr_results = await retrieve_authorized_chunks(
                    session,
                    query_embedding=vector(1.0, 0.0),
                    verified_roles=frozenset({AccessRole.HR}),
                    top_k=10,
                    minimum_score=-1.0,
                )
                employee_results = await retrieve_authorized_chunks(
                    session,
                    query_embedding=vector(1.0, 0.0),
                    verified_roles=frozenset({AccessRole.EMPLOYEE}),
                    top_k=10,
                    minimum_score=-1.0,
                )
                scoped_results = await retrieve_authorized_chunks(
                    session,
                    query_embedding=vector(1.0, 0.0),
                    verified_roles=frozenset({AccessRole.EMPLOYEE}),
                    top_k=10,
                    minimum_score=-1.0,
                    query_text="salary policy",
                    document_ids=[hr_document],
                )

                created_document_ids = {
                    hr_document,
                    manager_document,
                    common_document,
                }
                hr_created_results = {
                    result.document_id
                    for result in hr_results
                    if result.document_id in created_document_ids
                }
                employee_created_results = {
                    result.document_id
                    for result in employee_results
                    if result.document_id in created_document_ids
                }
                self.assertEqual(
                    hr_created_results,
                    {hr_document, common_document},
                )
                self.assertNotIn(manager_document, hr_created_results)
                self.assertEqual(
                    employee_created_results,
                    {common_document},
                )
                self.assertEqual(scoped_results, [])
                await validate_authorized_document_scope(
                    session,
                    frozenset({AccessRole.EMPLOYEE}),
                    [common_document],
                )
                for unavailable_id in (
                    hr_document,
                    inactive_document,
                    uuid.uuid4(),
                ):
                    with self.assertRaises(DocumentScopeError):
                        await validate_authorized_document_scope(
                            session,
                            frozenset({AccessRole.EMPLOYEE}),
                            [unavailable_id],
                        )
            finally:
                await transaction.rollback()


if __name__ == "__main__":
    unittest.main()
