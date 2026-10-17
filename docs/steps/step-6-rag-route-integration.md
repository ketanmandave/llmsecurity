# Step 6 - Publish Secure RAG Through SentinelAI

## Outcome

Secure RAG is now registered in the SentinelAI FastAPI application under one
versioned namespace:

```text
/api/v1/rag
```

The integration does not introduce another login route, token format, or role
parameter. Every endpoint uses the normal SentinelAI bearer token.

## Public endpoints

Authenticated employee-facing endpoints:

```text
POST /api/v1/rag/query
POST /api/v1/rag/retrieval/search
```

Administrator-only document endpoints:

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

## Request security flow

```text
Bearer token
    -> SentinelAI get_current_user
    -> active User + database Role
    -> RAG Principal(role_id from database)
    -> endpoint permission check
    -> role-filtered RAG operation
```

Document-management endpoints additionally pass through SentinelAI's
`get_administrator_user`. Query and retrieval endpoints accept any active
SentinelAI user, but document evidence remains limited by that user's role ID
inside the retrieval SQL query.

The request body never accepts the caller's role.

## Implementation

- `backend/app/rag/api/router.py` combines all RAG child routers.
- `backend/app/main.py` mounts that router at `/api/v1/rag`.
- Child route prefixes are relative (`/documents`, `/retrieval`, and `/query`)
  so `/v1` is declared only once by SentinelAI.
- Obsolete standalone JWT configuration was removed from the RAG settings.
- `backend/tests/test_rag_route_contract.py` verifies the complete route table,
  dependency boundaries, absence of legacy `/v1/...` paths, and OpenAPI output.

## Verification results

Focused automated tests:

```text
5 passed
```

This includes the Step 5 identity/schema tests and the Step 6 route-contract
tests.

Live isolated-stack checks:

| Check | Result |
| --- | --- |
| Backend health | healthy |
| PostgreSQL health | healthy |
| Redis health | healthy |
| RAG paths in OpenAPI | all 12 operations present |
| No token on admin endpoint | `401 Unauthorized` |
| Employee token on admin endpoint | `403 Forbidden` |
| Administrator token on admin endpoint | `200 OK` |
| Malicious employee retrieval prompt | `400 Blocked` |
| Roles returned by upload configuration | all 6 database roles |
| Native-text-only upload flag | enabled |

The six dynamic role slugs observed were:

```text
employee
hr
manager
payroll_administrator
security_analyst
sentinelai_administrator
```

## Running the updated backend

The backend image must be rebuilt once because Step 4 added new Python runtime
dependencies. From the SentinelAI project directory run:

```powershell
docker compose up -d --build
```

The disposable validation container received the missing packages directly to
avoid a full test-image rebuild. That temporary installation is not the
deployment mechanism; `backend/requirements.txt` is the permanent dependency
source for a clean build.

After startup, confirm:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Remaining integration work

The RAG routes are operational, but SentinelAI workspace conversations do not
yet call them. The next step should add an explicit `assistant` versus `rag`
message mode, route RAG answers through SentinelAI response security, persist
the answer and citations with the conversation, and return them to the
frontend.

> Step 7 status: this conversation and frontend integration is now complete.
> See `docs/steps/step-7-rag-conversation-integration.md`.
