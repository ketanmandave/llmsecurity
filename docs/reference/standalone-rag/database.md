# Database design

The RAG service is designed for one company. There is intentionally no tenant
column or tenant table.

## Relationship overview

```text
documents 1 ──────── * document_roles
    │
    └─────────────── * chunks
                         │
documents 1 ── * security_findings * ── 0..1 chunks

audit_events records request decisions and the IDs of documents used.
```

## Authorization model

`document_roles` is the source of truth for document access. A document is
eligible for retrieval only when it is active, its chunk is approved, and at
least one verified user role matches a `document_roles` row.

```sql
WHERE documents.status = 'active'
  AND chunks.security_status = 'approved'
  AND EXISTS (
      SELECT 1
      FROM document_roles
      WHERE document_roles.document_id = documents.id
        AND document_roles.role = ANY (:verified_roles)
  )
```

Roles are initially restricted to `admin`, `hr`, `manager`, and `employee`.
They are lowercase stable identifiers shared with the backend JWT contract.

## Key choices

- PostgreSQL is the source of truth for document metadata and permissions.
- pgvector stores 384-dimensional embeddings and provides an HNSW cosine index.
- Permissions are linked to documents, so permission changes do not require
  regenerating embeddings.
- Every native-text chunk retains `content_type`,
  `source_type`, page number, token count, and processor metadata. Its permission
  remains inherited from the source document through the same SQL authorization
  join; derivative text never receives an independent ACL.
- Original PDFs are referenced by `storage_key`; their bytes do not live in the
  database.
- User accounts remain in the company backend. The RAG service stores only the
  verified external user ID needed for auditing.
- Audit records contain identifiers and structured decision details, not raw
  prompts or complete generated answers.
- Deleting a document cascades to its permissions, chunks, and security findings.

## Schema lifecycle

Start the database and apply the schema with:

```bash
docker compose up -d database
alembic upgrade head
```

The embedding dimension is persisted in the schema. Changing to an embedding
model with a different dimension requires a migration and document re-indexing.
