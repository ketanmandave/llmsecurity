# Secure role-aware RAG: architecture and execution flow

This guide explains which file runs at every stage, from application startup to
PDF ingestion and role-authorized answers. Paths are relative to the repository
root.

## 1. System components

| Component | Responsibility | Main files |
|---|---|---|
| FastAPI application | HTTP routing, dependency injection, security headers | `app/main.py`, `app/api/` |
| Authentication | Verify JWT signature and claims; create the trusted principal | `app/auth/jwt.py`, `app/auth/permissions.py` |
| Document management | Upload PDFs, maintain roles, activate/deactivate/delete | `app/api/documents.py`, `app/services/document_service.py` |
| Ingestion | Extract, scan, chunk, embed, and publish native PDF text | `app/ingestion/`, `app/retrieval/embedder.py` |
| Retrieval | Apply roles inside SQL, find candidates, and rerank | `app/retrieval/`, `app/api/query.py` |
| Answer generation | Build grounded prompts, call Groq, validate citations | `app/services/query_service.py`, `app/generation/`, `app/api/rag.py` |
| Runtime security | Rate limit and inspect user input, retrieved context, output | `app/security/` |
| Persistence | PostgreSQL models, pgvector, sessions, migrations | `app/models/`, `app/database.py`, `migrations/` |
| Operations | Redis, Docker services, health/readiness | `docker-compose.yml`, `Dockerfile`, `app/api/health.py` |
| Admin UI | Upload, permissions, status, activation, deletion | `app/static/admin/` |

## 2. Application startup

```text
docker compose up
  -> Dockerfile builds the Python API image
  -> docker-compose.yml starts database and Redis
  -> API command runs `alembic upgrade head`
  -> migrations/versions/*.py updates PostgreSQL
  -> uvicorn imports app.main:app
  -> app/main.py registers all API routers and static admin files
```

`app/config.py` reads `.env` and validates settings. `app/database.py` creates the
async SQLAlchemy engine and session factory. `app/main.py` registers:

- `/health` and `/ready` from `app/api/health.py`
- `/v1/auth/me` from `app/api/auth.py`
- `/v1/documents/*` from `app/api/documents.py`
- `/v1/retrieval/search` from `app/api/query.py`
- `/v1/query` from `app/api/rag.py`
- `/admin` and `/admin/assets/*` for the dashboard

## 3. Authentication flow

Every protected endpoint declares either `get_current_principal` or
`require_admin` as a FastAPI dependency.

```text
Authorization: Bearer <JWT>
  -> app/auth/jwt.py:get_current_principal
  -> decode_access_token verifies HS256 signature, issuer, audience, expiry, sub
  -> role strings are converted to AccessRole values
  -> Principal(user_id, verified roles) is passed to the controller
  -> app/auth/permissions.py:require_admin additionally requires the admin role
```

The request body never decides the caller's roles. Only verified JWT claims become
the trusted `Principal`. `scripts/create_dev_token.py` creates local testing tokens
that follow this contract.

## 4. Document upload and ingestion flow

The browser starts in `app/static/admin/app.js:uploadDocument`. It sends a
`multipart/form-data` request containing the PDF, document name, classification,
and allowed roles.

```text
POST /v1/documents
  -> app/api/documents.py:upload_document                 [controller]
  -> app/auth/permissions.py:require_admin               [admin authorization]
  -> app/services/document_service.py:parse_allowed_roles
  -> app/services/document_service.py:create_document    [upload service]
       -> store_pdf                                      [extension/MIME/magic/size]
       -> app/ingestion/parser.py:validate_pdf_structure [valid PDF/pages/password]
       -> app/ingestion/parser.py:extract_pdf_pages      [native text required]
       -> duplicate checksum policy
       -> Document + DocumentRole rows
  -> commit document row
  -> app/ingestion/pipeline.py:run_ingestion_job          [background task]
       -> process_document
       -> extract_pdf_pages                              [page-aware text]
       -> app/ingestion/scanner.py:scan_and_redact_pages
          -> redact PII
          -> quarantine prompt-injection patterns
       -> app/ingestion/chunker.py:chunk_pages           [overlapping chunks]
       -> app/retrieval/embedder.py:embed_documents      [local vectors]
       -> Chunk rows with content_type=text, source_type=pymupdf
       -> Document status becomes active
```

The API rejects scanned or image-only PDFs with HTTP 422 before creating the
document row. This project intentionally does not use OCR or image understanding.

### Status outcomes

| Status | Meaning | Retrieval behavior |
|---|---|---|
| `processing` | Background ingestion is running | Excluded |
| `active` | Approved text chunks and vectors exist | Eligible, subject to role ACL |
| `quarantined` | Stored prompt-injection pattern found | Excluded |
| `failed` | Parsing, embedding, or persistence failed | Excluded |
| `inactive` | Admin deliberately deactivated it | Excluded |

## 5. Database records created during upload

`app/models/document.py` defines:

- `Document`: file metadata, classification, lifecycle status, uploader, error,
  and processing metadata.
- `DocumentRole`: one allowed role for one document. Together these rows form the
  document ACL.

`app/models/chunk.py` defines `Chunk`: sanitized text, page number, deterministic
hash, source metadata, approval state, and a 384-dimensional pgvector embedding.

`app/models/audit.py` defines security findings and privacy-conscious request audit
events. Raw questions, answers, JWTs, and matched PII are not stored in audit data.

## 6. Authorized retrieval flow

Call this endpoint when the caller needs evidence chunks without an LLM answer.

```text
POST /v1/retrieval/search
  -> app/api/query.py:search_authorized_documents        [controller]
  -> app/auth/jwt.py:get_current_principal               [verified roles]
  -> app/security/rate_limit.py:RateLimiter.check        [Redis]
  -> app/security/input_guard.py:inspect_user_input      [block/redact]
  -> app/retrieval/retriever.py:validate_authorized_document_scope
  -> app/retrieval/embedder.py:embed_query
  -> app/retrieval/retriever.py:retrieve_authorized_chunks
  -> app/retrieval/ranking.py:rank_candidates
       -> app/retrieval/reranker.py:LocalReranker
  -> app/security/context_guard.py:inspect_retrieved_chunks
  -> app/services/audit_service.py:write_audit_event
  -> RetrievalResponse
```

The important authorization is in
`app/retrieval/retriever.py:retrieve_authorized_chunks`. Its PostgreSQL query
requires all of the following before a chunk can leave the database:

1. The document is `active`.
2. The chunk is `approved` and has an embedding.
3. The chunk has `content_type = text`.
4. A `document_roles` row matches at least one verified JWT role.
5. Optional `document_ids` contain that document.
6. Vector similarity meets the candidate threshold.

The optional document IDs only narrow the search. They never bypass role checks.
Hybrid ranking combines vector similarity, lexical content matches, title matches,
and local cross-encoder scores. Final thresholds remove unrelated accessible
documents before results are returned.

## 7. Grounded answer flow

Call this endpoint when the caller wants the final natural-language answer.

```text
POST /v1/query
  -> app/api/rag.py:query_documents                      [controller]
  -> JWT verification, Redis rate limit, input guard
  -> app/services/query_service.py:answer_authorized_query
       -> validate_authorized_document_scope
       -> embed_query
       -> retrieve_authorized_chunks                    [role filter in SQL]
       -> rank_candidates
       -> inspect_retrieved_chunks
       -> app/generation/prompts.py:build_generation_messages
       -> app/generation/llm.py:GroqLLMService.generate
       -> app/generation/citations.py:validate_and_build_citations
       -> app/security/output_guard.py:inspect_model_output
  -> write privacy-safe audit event
  -> RAGQueryResponse(answer, grounded, sources, model)
```

`app/generation/prompts.py` labels every retrieved chunk with a temporary source
ID. Groq must return strict JSON matching `ModelAnswer`. The model may cite only
those source IDs. `app/generation/citations.py` rejects unknown or missing citations
and maps valid IDs back to real document, page, and chunk identifiers. If there is
no authorized evidence, Groq is not called and the API returns the standard
insufficient-information answer.

## 8. Document lifecycle controllers

All routes below are in `app/api/documents.py` and require an admin JWT.

| Request | Controller | Service behavior |
|---|---|---|
| `GET /v1/documents` | `get_documents` | List documents and ACLs |
| `GET /v1/documents/{id}/status` | `get_document_status` | Count chunks/findings |
| `PATCH /v1/documents/{id}/access` | `update_document_access` | Replace all allowed roles |
| `POST /v1/documents/{id}/process` | `retry_document_processing` | Queue ingestion again |
| `DELETE /v1/documents/{id}` | `delete_document` | Set status to inactive |
| `POST /v1/documents/{id}/activate` | `reactivate_document` | Reuse native-text vectors or reprocess |
| `DELETE /v1/documents/{id}/permanent` | `permanently_delete_document_route` | Delete PDF, ACL, chunks, vectors, findings |

Most persistence logic is in `app/services/document_service.py`, keeping HTTP
controllers small and leaving transaction logic reusable and testable.

## 9. Security pipeline

Security is applied at multiple boundaries:

```text
JWT verification
  -> per-user Redis rate limit
  -> user-input inspection and redaction
  -> role authorization inside retrieval SQL
  -> retrieved-context inspection
  -> constrained LLM prompt and JSON schema
  -> citation validation
  -> model-output inspection and redaction
  -> hashed, privacy-safe audit record
```

`app/security/policy.py` combines decisions using the strictest result. A block is
never weakened by a later allow decision.

## 10. File-by-file reading order

For a first walkthrough, read the code in this order:

1. `app/main.py` — application assembly and route registration.
2. `app/config.py` — environment-controlled behavior and validation.
3. `app/auth/jwt.py` — trusted identity and role extraction.
4. `app/api/documents.py` — upload and lifecycle controllers.
5. `app/services/document_service.py` — PDF storage and ACL persistence.
6. `app/ingestion/pipeline.py` — the complete indexing transaction.
7. `app/api/query.py` — retrieval-only controller and security checks.
8. `app/retrieval/retriever.py` — role-aware SQL query.
9. `app/retrieval/ranking.py` — relevance filtering and reranking.
10. `app/api/rag.py` — final answer controller.
11. `app/services/query_service.py` — retrieval-to-Groq orchestration.
12. `app/generation/` — prompts, Groq adapter, and citation validation.
13. `app/models/` and `migrations/` — persisted data structure.
14. `app/static/admin/` — browser dashboard.
15. `tests/` — executable examples proving each security boundary.

## 11. Where to debug common problems

| Symptom | Start here |
|---|---|
| Upload returns 415/413/422 | `app/services/document_service.py`, `app/ingestion/parser.py` |
| Document remains failed/quarantined | `app/ingestion/pipeline.py`, container logs, `security_findings` |
| Authorized user gets no chunks | JWT roles, document status/ACL, `app/retrieval/retriever.py`, ranking thresholds |
| Unrelated document appears | `app/retrieval/ranking.py` thresholds and optional `document_ids` |
| Query gets 429/503 | `app/security/rate_limit.py`, Redis readiness |
| Query has no answer | authorized evidence, relevance threshold, context guard, Groq configuration |
| Citation error | `app/generation/citations.py` and Groq structured output |
| Admin page cannot connect | admin token, `/v1/auth/me`, `/ready`, browser session storage |

