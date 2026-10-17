# Step 12 — Repository restructure

## Outcome

The nested imported application and the old standalone RAG root were
consolidated into one authoritative repository layout. This removes ambiguous
Python imports and makes Docker, backend, frontend, tests, models, and documents
all resolve from the same root.

## Final structure

```text
backend/      FastAPI host application and namespaced app.rag module
frontend/     React/Vite application
docker/       container build files
docs/         categorized current and historical documentation
samples/      PDF fixtures for manual testing
```

Project-level `.env.example`, Compose files, ignore files, and `README.md` stay
at the repository root.

## Removed duplication

- Removed the obsolete standalone root `app` package.
- Removed standalone Alembic migrations and requirements files.
- Removed the obsolete SQL seed schema and seed script.
- Promoted the integrated `backend`, `frontend`, and Docker files to the root.
- Removed the empty `sentinel-ai-college-main` wrapper directory.

The old tracked files remain recoverable from Git history. Untracked research
documents, diagrams, sample PDFs, uploads, and model cache were preserved.

## Import safety

All backend imports retain the `app.*` namespace. The package is now located at
`backend/app`, and Python commands must run from `backend` (or inside the
backend container). RAG remains at `app.rag`, avoiding collisions with shared
SentinelAI models, services, authentication, and gateway modules.

## Docker safety

The normal Compose project now has the explicit name `sentinelai-college`, so it
cannot accidentally reuse the old standalone project's `llmsecurity_*` volumes.
The baseline project remains `sentinel-baseline` and continues to use its
preserved verification database volume.

## Verification after the move

- Both Compose configurations parsed successfully.
- Every backend application and test file compiled successfully.
- No active source or current step document references the removed nested path.
- Backend suite: **47 passed**.
- Frontend production build: **passed**.
- Backend, PostgreSQL, and Redis health checks: **healthy**.
