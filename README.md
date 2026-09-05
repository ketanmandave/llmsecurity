# Secure Role-Aware RAG

Backend service for ingesting company documents with role-based access rules and
retrieving only the chunks authorized for the authenticated user.

## Current status

Steps 2 through 10 are complete: project structure, PostgreSQL/pgvector schema,
document management, ingestion, JWT role extraction, authorized vector retrieval,
Groq generation with validated citations, and runtime security controls are
implemented. The service is packaged for deployment and has a backend/frontend
handover contract.

## Main packages

- `app/api`: HTTP endpoints
- `app/auth`: JWT verification and role authorization
- `app/ingestion`: document parsing, scanning, chunking, and indexing
- `app/retrieval`: embeddings, authorized search, and reranking
- `app/generation`: LLM integration, prompts, and citations
- `app/security`: input, context, and output guards
- `app/models`: database and request/response models
- `app/services`: application orchestration services
- `tests`: unit and integration tests

The backend authentication contract is documented in `docs/authentication.md`.
The complete API integration and deployment contract is documented in
`docs/integration-handover.md`.

## Administrator dashboard

Open `http://127.0.0.1:8000/admin` and connect with a short-lived JWT containing
the `admin` role. The dashboard can upload PDFs, select allowed roles and data
classification, monitor ingestion status, search the document library, replace
permissions, retry failed or quarantined ingestion, and deactivate documents.
Administrators can also permanently delete a document and all of its indexed data.
The token is retained only in browser `sessionStorage` and is removed when the
admin disconnects or closes the tab.

## Database model

- `documents`: uploaded-file metadata and processing state
- `document_roles`: roles permitted to retrieve each document
- `chunks`: parsed text, source location, scan status, and 384-dimensional vector
- `audit_events`: privacy-conscious request and policy-decision records
- `security_findings`: PII, prompt-injection, and other scanner findings

User accounts are intentionally not duplicated here. The company backend remains
the identity source and this service records its external user ID after JWT
verification.

Apply the initial schema after PostgreSQL with pgvector is available:

```bash
alembic upgrade head
```

## Document-management API

All document-management endpoints require a backend-issued JWT containing the
`admin` role.

Upload a PDF using `multipart/form-data`:

```text
POST /v1/documents
file=<PDF>
name=Employee Leave Policy
allowed_roles=["employee", "hr", "manager"]
classification=internal
```

The upload endpoint validates the `.pdf` extension, PDF magic bytes, configured
size limit, and allowed role identifiers. It stores the file under a generated
server-side name and starts background ingestion. The pipeline extracts text with
page numbers, redacts common PII, quarantines likely document prompt injections,
creates overlapping chunks, generates local embeddings, and activates the document.

Other administrator endpoints:

```text
GET    /v1/documents
GET    /v1/documents/{document_id}
GET    /v1/documents/{document_id}/status
PATCH  /v1/documents/{document_id}/access
POST   /v1/documents/{document_id}/process
POST   /v1/documents/{document_id}/activate
DELETE /v1/documents/{document_id}
DELETE /v1/documents/{document_id}/permanent
```

`DELETE` safely changes the status to `inactive`; it does not immediately erase
the file or database record. The `/permanent` endpoint irreversibly removes the
document record, role permissions, chunks and vectors, security findings, and
stored PDF. Historical audit events are retained but cannot be retrieved as RAG
content.

`POST /activate` restores an inactive document immediately when approved vectors
remain. If it has no reusable chunks, the endpoint starts ingestion again and
returns `reprocessing: true` until the document becomes active.

The first ingestion run downloads the configured embedding model and can take
longer than later runs. Image-only PDFs currently fail with a clear OCR-required
status; OCR support is a later enhancement. The in-process background runner is
appropriate for the MVP. A durable Redis-backed worker should replace it before
multi-instance production deployment.

## Authorized retrieval API

Any authenticated company role can call:

```text
POST /v1/retrieval/search
```

with:

```json
{
  "question": "What is the employee leave policy?",
  "top_k": 5
}
```

To limit a question to documents the user selected, optionally include their IDs:

```json
{
  "question": "Which topics are given for ISE of cybersecurity?",
  "top_k": 5,
  "document_ids": ["00000000-0000-0000-0000-000000000000"]
}
```

Document scope is an additional filter and never bypasses role authorization.
The service first applies document status, chunk security, verified JWT roles,
and optional document IDs inside PostgreSQL. It retrieves a wider candidate set,
then combines semantic similarity, keyword/title matches, and a local
cross-encoder score. A minimum threshold and a best-result-relative cutoff remove
weak but role-accessible chunks before `top_k` is applied. This prevents an
unrelated accessible document, such as a résumé, from being supplied to the LLM
merely because it has a non-zero embedding similarity.

The response includes the final `score` plus `vector_score`, `lexical_score`,
`title_score`, and `reranker_score` for debugging. The embedding and reranking
models run locally. Their first use downloads model files into
`MODEL_CACHE_DIRECTORY`; subsequent requests reuse that cache.

## Grounded answer API

Set a Groq key in `.env` and restart the API:

```text
GROQ_API_KEY=your-key-from-groq
GROQ_MODEL=openai/gpt-oss-120b
```

Then call `POST /v1/query`:

```json
{
  "question": "What is polymorphism?",
  "top_k": 5,
  "document_ids": null
}
```

The endpoint uses only role-authorized chunks, sends bounded and escaped source
blocks to Groq, requires strict structured output, rejects unknown citation IDs,
and maps valid citations back to document, page, and chunk IDs. If retrieval finds
no authorized evidence, it returns a standard insufficient-information answer
without calling Groq.

## Runtime security controls

Both query endpoints enforce a Redis-backed per-user rate limit before embedding
or generation. User input is inspected for prompt injection and sensitive values;
retrieved chunks are scanned again to prevent stored prompt injection; generated
answers are redacted before being returned. Each decision is written to
`audit_events` with hashes, finding categories, role information, document IDs,
counts, and latency. Raw questions, retrieved text, answers, credentials, and PII
are not stored in audit details.

The rate limiter intentionally fails closed when Redis is unavailable. Configure
`RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` in `.env` for the expected
traffic level.

## Run locally on Windows

From PowerShell in the repository directory:

```powershell
Copy-Item .env.example .env
docker compose up -d database redis
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\uvicorn.exe app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. In a second PowerShell window, create a
short-lived development administrator token:

```powershell
.venv\Scripts\python.exe scripts\create_dev_token.py --user-id admin-001 --roles admin
```

Copy the printed token, select **Authorize** in Swagger, and paste the token.
You can then call `POST /v1/documents`; send `allowed_roles` as either a JSON string
such as `["hr", "manager"]` or a comma-separated string such as `hr,manager`.

The token helper refuses to run outside development mode. Replace the example
JWT secret before sharing or deploying the service.

## Run the packaged stack

After configuring `.env`, build and start the API, PostgreSQL, and Redis together:

```powershell
docker compose up -d --build
docker compose ps
```

The API is available at `http://127.0.0.1:8000`, with liveness at `/health`
and dependency readiness at `/ready`. To run the integration smoke test, set a
short-lived token in `RAG_ACCESS_TOKEN` and run:

```powershell
.\scripts\smoke_test.ps1
```
