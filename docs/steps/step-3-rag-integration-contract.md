# Step 3 — SentinelAI and Secure RAG Integration Contract

Date: 2026-10-12

## Decision

SentinelAI remains the main application and security gateway. Secure RAG becomes an internal backend capability of SentinelAI rather than a second public application with its own users, JWTs, roles, and frontend.

This step defines the integration boundary only. RAG source migration begins in the next implementation step.

## Target request flow

```text
SentinelAI frontend
    |
    v
SentinelAI authentication and session validation
    |
    v
SentinelAI authorization + prompt security + risk/policy decision
    |
    +---- blocked/reviewed request ---> security event + safe response
    |
    v
Secure RAG service
    |
    +--> embed question
    +--> vector/lexical retrieval with role ACL inside the SQL query
    +--> retrieved-context security scan
    +--> grounded Groq generation
    +--> citation validation
    |
    v
SentinelAI response-security pipeline
    |
    v
Conversation/message persistence + audit/security events
    |
    v
Safe answer and citations returned to the frontend
```

## Ownership boundaries

| Concern | Authoritative component |
| --- | --- |
| Users and passwords | SentinelAI |
| Access and refresh tokens | SentinelAI |
| Active/inactive user check | SentinelAI |
| Company roles | SentinelAI `roles` table |
| Prompt security, risk, and policy decision | SentinelAI gateway |
| Document metadata and ACLs | Secure RAG module |
| Chunking, embeddings, retrieval, and citations | Secure RAG module |
| Response security | SentinelAI gateway, with RAG context guards retained as defense in depth |
| Conversations and messages | SentinelAI |
| Platform security events | SentinelAI |
| RAG retrieval/ingestion diagnostics | RAG audit records linked by request/user/conversation identifiers |

## Authentication contract

The browser sends only the normal SentinelAI access token.

The integrated RAG routes use SentinelAI's `get_current_user` dependency. They must not:

- accept a role from request JSON or form data;
- trust a role supplied by the frontend;
- issue a second RAG token;
- decode the same token with separate RAG issuer/audience settings;
- accept the current Secure RAG development-token endpoint in production.

The backend loads the active user and role from SentinelAI's database. The normalized database role is passed to retrieval as trusted server-side context.

## Role and ACL contract

SentinelAI currently provides these roles:

| SentinelAI role | Normalized ACL slug |
| --- | --- |
| Employee | `employee` |
| Manager | `manager` |
| HR | `hr` |
| Payroll Administrator | `payroll_administrator` |
| Security Analyst | `security_analyst` |
| SentinelAI Administrator | `admin` |

The existing RAG `AccessRole` enum supports only `admin`, `hr`, `manager`, and `employee`. It must not remain the database authority after integration.

Target design:

- `document_roles.role_id` references SentinelAI `roles.id`.
- Role names/slugs are returned dynamically by the upload-configuration endpoint.
- Adding a SentinelAI role does not require creating a PostgreSQL enum migration.
- Administrators manage document ACLs by role ID.
- Retrieval joins `chunks -> documents -> document_roles` and filters by the authenticated user's `role_id` before ranking.
- Inactive, failed, quarantined, or deleted documents are excluded in the same query.

This prevents privilege decisions from being performed only in Python or in the browser.

## Database contract

Use one PostgreSQL database and enable the `vector` extension. Preserve the existing SentinelAI tables and add the RAG tables through one ordered migration chain.

RAG tables to add:

- `documents`
- `document_roles`
- `chunks`
- `audit_events` (or a renamed `rag_audit_events` table if naming clarity is preferred)
- `security_findings`

Required relationship changes:

- `documents.uploaded_by` becomes a foreign key to SentinelAI `users.id`.
- `document_roles.role_id` becomes a foreign key to SentinelAI `roles.id`.
- RAG request/audit records store SentinelAI `user_id`, `conversation_id`, and shared `request_id` where applicable.

Do not run the current RAG Alembic history directly against the SentinelAI database. Create new integration migrations from the combined target schema so existing SentinelAI data is preserved.

## Public API contract

All integrated endpoints use SentinelAI's `/api/v1` namespace.

### Employee/authorized-user endpoints

```text
POST /api/v1/rag/query
POST /api/v1/rag/retrieval/search
```

`POST /api/v1/rag/query` request:

```json
{
  "question": "What is the employee leave policy?",
  "conversation_id": "sentinel-conversation-id",
  "top_k": 5,
  "document_ids": null
}
```

Roles are intentionally absent from the request.

Response:

```json
{
  "request_id": "uuid",
  "answer": "Grounded answer",
  "grounded": true,
  "sources": [
    {
      "source_id": "S1",
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_name": "Leave Policy",
      "page_number": 3,
      "content_type": "text",
      "source_type": "pymupdf"
    }
  ],
  "model": "openai/gpt-oss-120b"
}
```

### Administrator endpoints

```text
POST   /api/v1/rag/documents
GET    /api/v1/rag/documents
GET    /api/v1/rag/documents/config
GET    /api/v1/rag/documents/{document_id}
PATCH  /api/v1/rag/documents/{document_id}/access
GET    /api/v1/rag/documents/{document_id}/status
POST   /api/v1/rag/documents/{document_id}/process
POST   /api/v1/rag/documents/{document_id}/activate
DELETE /api/v1/rag/documents/{document_id}
DELETE /api/v1/rag/documents/{document_id}/permanent
```

Every administrator endpoint uses SentinelAI's `get_administrator_user` dependency.

## Conversation integration

The employee workspace should expose an explicit knowledge-source mode rather than silently guessing whether every prompt needs RAG.

Recommended message request extension:

```json
{
  "content": "What is our leave policy?",
  "mode": "rag",
  "document_ids": null
}
```

Supported modes:

- `assistant`: current general SentinelAI provider flow.
- `rag`: role-authorized company-document flow with citations.

The backend, not the frontend, executes the security and authorization chain for either mode.

## Frontend contract

The standalone Secure RAG `/admin` page will not remain a separate application after migration.

Target SentinelAI frontend additions:

- `Documents` navigation item in the administrator console.
- Upload form containing file, name, classification, and dynamically loaded allowed roles.
- Document library with processing status, ACL editing, deactivate/reactivate, and permanent-delete controls.
- Employee chat mode selector for `Assistant` versus `Company Knowledge`.
- Citation cards beneath grounded RAG responses.

## Package compatibility decisions

Keep SentinelAI's pinned security-model packages:

- `torch==2.6.0`
- `transformers==4.48.3`
- `safetensors==0.5.3`

Add the RAG-only dependencies to the SentinelAI backend requirements:

- `asyncpg`
- `fastembed`
- `groq`
- `pgvector`
- `PyMuPDF`
- `pydantic-settings`

Existing common packages such as FastAPI, SQLAlchemy, Redis, PyJWT, psycopg, multipart, and Uvicorn must have one compatible version constraint each.

## Target backend layout

```text
backend/app/
  api/routes/
    rag_documents.py
    rag_query.py
    rag_retrieval.py
  rag/
    ingestion/
    retrieval/
    generation/
    security/
    services/
    schemas/
  models/
    document.py
    document_role.py
    chunk.py
    rag_audit_event.py
    security_finding.py
```

Namespacing the imported code under `app.rag` avoids collisions with SentinelAI's existing `app.gateway`, `app.security`, `app.services`, and `app.models` modules.

## Security invariants

The implementation is acceptable only if all of these remain true:

1. The client cannot select its own role.
2. Database retrieval applies the role filter before similarity ranking.
3. Explicit `document_ids` are validated against the authenticated role.
4. Only active documents and approved chunks can be retrieved.
5. An unrelated question can return no evidence rather than forcing a weak match.
6. The model receives only authorized, scanned context.
7. Citations reference chunks actually used to produce the answer.
8. Deactivation immediately removes a document from retrieval.
9. Permanent deletion removes the document, ACL rows, chunks/vectors, findings, and stored file.
10. Shared request identifiers connect SentinelAI security events with RAG audit events.

## Step 3 acceptance result

The target ownership, authentication, role mapping, database relationships, API namespace, conversation behavior, frontend responsibilities, and security invariants are now defined.

The next implementation step should create the combined dependency/configuration foundation and namespaced RAG package without yet modifying production conversation behavior.

Step 4 completed that source migration. Its manifest and verification results
are recorded in `docs/steps/step-4-rag-source-migration.md`.
