# Antigravity handoff prompt

Continue building and maintaining the Secure Role-Aware RAG project in this
repository. Inspect the existing code, migrations, tests, README, and documentation
before changing anything. Preserve working features and existing user data.

## Product scope

This is a single-company secure RAG backend. It accepts text-based PDF documents,
assigns each document one or more allowed roles (`admin`, `hr`, `manager`, or
`employee`), stores local embeddings in PostgreSQL/pgvector, and returns only
chunks the authenticated user's verified JWT roles can access. There is no tenant
ID because the system serves one company.

Do not add OCR, scanned-document processing, image understanding, chart analysis,
or a vision model. These features were intentionally removed to keep the major
project reliable and explainable. Scanned or image-only PDFs must return HTTP 422
with a clear message. A table is searchable only when its words exist in the PDF's
native text layer.

## Implemented architecture

- FastAPI application and Swagger API
- PostgreSQL with pgvector and Alembic migrations
- Redis-backed per-user rate limiting
- PyMuPDF native PDF text extraction
- Local `BAAI/bge-small-en-v1.5` embeddings
- Local cross-encoder reranking plus vector, lexical, and title signals
- Backend-issued HS256 JWT validation with issuer, audience, expiry, subject, and
  normalized role claims
- Groq `openai/gpt-oss-120b` for grounded answer generation
- PII redaction, prompt-injection checks, response scanning, and privacy-conscious
  audit events
- Admin dashboard at `/admin`
- Docker Compose services for API, PostgreSQL, and Redis

## Required ingestion behavior

1. The admin submits a PDF, display name, classification, and allowed roles.
2. Validate extension, MIME type, magic bytes, size, PDF structure, password state,
   page limit, permissions, and native extractable text before creating the row.
3. Extract text page by page with one-based page numbers.
4. Redact configured PII and quarantine instruction-like prompt injection.
5. Create overlapping chunks with `content_type=text` and
   `source_type=pymupdf`.
6. Generate local embeddings and store approved chunks in pgvector.
7. Mark the document active only after successful indexing.

## Required retrieval behavior

Authorization must be enforced inside the database query, never only in the UI or
after retrieval. Filter by active document, approved chunk, non-null embedding,
`content_type=text`, verified JWT roles, and optional requested document IDs.
Explicit IDs narrow the authorized scope and never bypass permissions. Reject an
explicit ID that is missing, inactive, or inaccessible. Apply relevance thresholds
and reranking so an unrelated but accessible document is not sent to the LLM.

## Document lifecycle

The admin dashboard supports upload, listing, permission replacement, retry,
deactivate, activate, and permanent deletion. Deactivation keeps the record and
vectors but excludes it from retrieval. Activation reuses approved vectors when
available or reprocesses the stored PDF. Permanent deletion removes the document,
ACL rows, chunks/vectors, security findings, and stored file; audit history remains.

## API and operations

Important endpoints include:

```text
GET    /health
GET    /ready
GET    /admin
POST   /v1/documents
GET    /v1/documents
GET    /v1/documents/config
PATCH  /v1/documents/{document_id}/access
POST   /v1/documents/{document_id}/process
POST   /v1/documents/{document_id}/activate
DELETE /v1/documents/{document_id}
DELETE /v1/documents/{document_id}/permanent
POST   /v1/retrieval/search
POST   /v1/query
```

`/ready` reports only traffic-critical database and Redis readiness. Groq is used
for final answer generation, not PDF extraction. Never expose secrets, raw tokens,
questions, retrieved text, or answers in logs or audit details.

Run locally with either host Uvicorn plus Docker database/Redis, or the full Docker
Compose stack, but never run two API processes on port 8000. Typical packaged
startup is:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Generate development tokens with `scripts/create_dev_token.py`. Keep
`GROQ_MODEL=openai/gpt-oss-120b`. Run `python -m unittest discover -s tests -v`
after changes and add focused tests for security, authorization, ingestion, and
document lifecycle behavior.

When editing, preserve unrelated uncommitted work, use migrations for schema
changes, avoid destructive database resets, keep role values consistent across
JWTs/uploads/database filters, and update README/docs/API schemas/dashboard/tests
together whenever a contract changes.
