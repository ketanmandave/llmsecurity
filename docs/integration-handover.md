# Secure RAG integration handover

This document is the contract between the RAG service and the company backend or
frontend teams. The backend remains the identity provider. The RAG service never
trusts a role supplied in a request body; it uses only roles from a verified JWT.

## Runtime endpoints

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | Process liveness |
| `GET` | `/ready` | Public | PostgreSQL and Redis readiness |
| `GET` | `/v1/auth/me` | Authenticated | Confirm verified user and roles |
| `POST` | `/v1/query` | Authenticated | Final secure RAG answer with citations |
| `POST` | `/v1/retrieval/search` | Authenticated | Authorized chunk search; keep backend-only |
| `POST` | `/v1/documents` | Admin | Upload PDF and assign allowed roles |
| `GET` | `/v1/documents` | Admin | Paginated document list |
| `GET` | `/v1/documents/{id}` | Admin | Document metadata and permissions |
| `GET` | `/v1/documents/{id}/status` | Admin | Ingestion status and counts |
| `PATCH` | `/v1/documents/{id}/access` | Admin | Replace document role permissions |
| `POST` | `/v1/documents/{id}/process` | Admin | Retry ingestion |
| `POST` | `/v1/documents/{id}/activate` | Admin | Reactivate existing vectors or restart ingestion when needed |
| `DELETE` | `/v1/documents/{id}` | Admin | Soft-deactivate document |
| `DELETE` | `/v1/documents/{id}/permanent` | Admin | Permanently remove document, vectors, ACL, findings, and PDF |

Interactive OpenAPI documentation is available at `/docs`.
The administrator document dashboard is available at `/admin` and requires a
short-lived JWT containing the `admin` role.

## Authentication contract

Send the company-backend JWT with every protected request:

```http
Authorization: Bearer <access-token>
```

The required claims and signing contract are in `docs/authentication.md`. Supported
roles are `admin`, `hr`, `manager`, and `employee`. A user's access is the union of
their verified roles. Never add `role` or `allowed_roles` to a query request.

## Query integration

Request:

```http
POST /v1/query
Content-Type: application/json
Authorization: Bearer <access-token>
```

```json
{
  "question": "What is the employee leave policy?",
  "conversation_id": "frontend-chat-42",
  "top_k": 5
}
```

Response:

```json
{
  "request_id": "e6599a8a-5f92-4e43-b6b8-3f28cae74f34",
  "answer": "Employees receive the leave entitlement described in the policy [S1].",
  "grounded": true,
  "sources": [
    {
      "source_id": "S1",
      "chunk_id": "c44d3ad5-326b-489a-a08a-c593dfdf6e58",
      "document_id": "ef35ba66-83bf-4610-9612-873b56fc9586",
      "document_name": "Employee Leave Policy",
      "page_number": 4
    }
  ],
  "model": "openai/gpt-oss-120b"
}
```

The frontend should display the answer and render each source as a citation. When
`grounded` is false, `sources` is empty and the answer explains that authorized
documents did not contain sufficient information. Do not retry that result with a
different role.

## Document upload workflow

Only an administrator token can upload or manage documents. Send a multipart form:

```text
file=<PDF bytes>
name=Employee Leave Policy
allowed_roles=["employee","hr","manager"]
classification=internal
```

The upload returns HTTP `202` with a `document_id`. Poll
`GET /v1/documents/{document_id}/status` until the status is `active`,
`quarantined`, or `failed`. A document cannot appear in retrieval until it is
`active`. Updating access replaces the complete permission set:

```json
{"allowed_roles":["hr","manager"]}
```

## Errors the client must handle

| Status | Meaning | Client behavior |
| --- | --- | --- |
| `400` | Security policy blocked the input | Show a safe validation message; do not auto-retry |
| `401` | Missing, invalid, or expired JWT | Refresh/sign in and retry once |
| `403` | Verified user lacks admin permission | Hide admin action and report forbidden |
| `404` | Document does not exist | Refresh document list |
| `413` | PDF exceeds configured size | Ask for a smaller PDF |
| `422` | Invalid request fields | Correct the submitted form or JSON |
| `429` | Per-user rate limit exceeded | Respect the `Retry-After` header |
| `502` | Model generation failed | Offer a later retry using the same user identity |
| `503` | Database, Redis, or LLM configuration unavailable | Treat service as temporarily unavailable |

Log the returned `request_id` in the calling application for support correlation.
Do not log bearer tokens, raw sensitive prompts, or complete model responses.

## Deployment contract

Required secrets and environment values:

- `GROQ_API_KEY`
- `JWT_SECRET_KEY` shared securely with the company backend
- `JWT_ISSUER` and `JWT_AUDIENCE`
- PostgreSQL credentials
- exact frontend origins in `CORS_ALLOWED_ORIGINS`

For the packaged local deployment:

```powershell
Copy-Item .env.example .env
# Fill GROQ_API_KEY and replace JWT_SECRET_KEY before starting.
docker compose up -d --build
docker compose ps
```

The API container applies Alembic migrations before starting one Uvicorn worker.
Use `/health` for liveness and `/ready` for readiness. One worker is intentional
because MVP ingestion uses FastAPI background tasks. Move ingestion to a durable
worker queue before horizontally scaling the API. Uploaded PDFs persist in the
host project's `uploads` directory; PostgreSQL data and the embedding-model cache
use Docker volumes.

## Acceptance checklist

- Backend-issued tokens pass `/v1/auth/me` with the expected roles.
- Employee, manager, HR, and admin tokens are tested against documents with
  different permissions.
- Unauthorized roles return no protected chunks or citations.
- PDF upload reaches `active` and produces chunks.
- `/ready` reports both PostgreSQL and Redis healthy.
- Rate-limit `429` handling respects `Retry-After`.
- Production secrets are supplied by a secret manager and are not committed.
- TLS terminates at the ingress or load balancer.
