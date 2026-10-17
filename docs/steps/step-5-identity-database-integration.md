# Step 5 - SentinelAI Identity and RAG Database Integration

## Outcome

The migrated RAG module now uses SentinelAI as its only authentication,
authorization, role, and database authority. The old standalone RAG JWT decoder
and fixed role enum are no longer used.

RAG API routes remain intentionally unregistered. They will be exposed only
after the route adapter and end-to-end authorization checks are completed.

## Authentication flow

1. A client signs in through SentinelAI and receives a SentinelAI access token.
2. SentinelAI's `get_current_user` dependency validates the token and loads the
   current `User` and its related `Role` from the database.
3. `app/rag/auth/jwt.py` converts that user into a small RAG `Principal`.
4. The principal contains the SentinelAI user ID, numeric role ID, role name,
   and a normalized role slug.
5. RAG services use the verified numeric role ID for every ACL filter. They do
   not trust a role supplied in a request body or query parameter.

Administrators are checked through SentinelAI's existing
`get_administrator_user` dependency. There is no second RAG login system.

## Dynamic role permissions

Document access is stored using SentinelAI role records rather than a fixed
Python enum:

- `document_roles.document_id` references `documents.id`.
- `document_roles.role_id` references `roles.id`.
- Upload and ACL-update requests accept role IDs.
- Role IDs are validated against the `roles` table before saving.
- Retrieval adds the authenticated user's verified role ID to the SQL/vector
  query, so inaccessible chunks never leave the database query.

This supports adding more SentinelAI roles without changing the RAG source
code. A new role becomes available after it exists in the `roles` table and an
administrator grants it access to a document.

## Combined database schema

RAG models now use SentinelAI's shared SQLAlchemy `Base`. Database startup
imports the RAG models before `Base.metadata.create_all`, enables the pgvector
extension, creates the RAG tables, and creates full-text-search indexes.

Important cross-module relationships:

| RAG column | SentinelAI target | Delete behavior |
| --- | --- | --- |
| `documents.uploaded_by` | `users.id` | RESTRICT |
| `document_roles.role_id` | `roles.id` | CASCADE |
| `audit_events.user_id` | `users.id` | RESTRICT |

The integrated RAG tables are:

- `documents`
- `document_roles`
- `chunks`
- `security_findings`
- `audit_events`

The SentinelAI Docker Compose database image is now
`pgvector/pgvector:pg16`, allowing vector columns and similarity search in the
same PostgreSQL database as users, roles, conversations, and security data.

## Main implementation files

- `backend/app/rag/auth/jwt.py` - adapts an authenticated SentinelAI user into
  a RAG principal.
- `backend/app/rag/auth/permissions.py` - reuses SentinelAI administrator
  authorization.
- `backend/app/rag/models/base.py` - re-exports SentinelAI's shared model base.
- `backend/app/rag/models/document.py` - document and role ACL relationships.
- `backend/app/rag/models/audit.py` - RAG audit-to-user relationship.
- `backend/app/rag/services/document_service.py` - validates and stores role-ID
  permissions.
- `backend/app/rag/retrieval/retriever.py` - applies role authorization inside
  retrieval queries.
- `backend/app/database/init_db.py` - initializes pgvector, all shared tables,
  and RAG search indexes.

## Verification performed

- Python source compilation passed.
- Focused identity and schema tests passed: **2 passed**.
- PostgreSQL pgvector extension was enabled and reported version `0.8.7`.
- RAG tables and foreign keys were inspected in the isolated baseline database.
- Combined backend startup completed successfully.
- Backend, PostgreSQL, and Redis health checks returned healthy.
- SentinelAI employee and administrator login still returned valid tokens.

The previously recorded unrelated SentinelAI baseline test failures were not
caused by this step. They concern the semantic-model expectation, rate-limit
state, and risk-score behavior and remain separate baseline work.

## Security properties achieved

- One trusted token issuer and one user database.
- The server derives roles from the authenticated database user.
- No client-provided role can broaden document access.
- Retrieval permission checks happen in the database query.
- Upload ownership and audit records point to real SentinelAI users.
- Role definitions are data-driven and extensible.

## Next step

Create the `/api/v1/rag` route adapters, register them in SentinelAI, and run
end-to-end tests proving that administrator upload, employee retrieval, denied
access, deactivation, deletion, generation, and citations all work through the
combined application.

> Step 6 status: the route adapters and authentication-boundary checks are now
> complete. See `docs/steps/step-6-rag-route-integration.md`.
