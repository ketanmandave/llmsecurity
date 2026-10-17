# Step 10 — Release Readiness and Handoff

## Outcome

The role-aware RAG module is integrated into SentinelAI and was verified from a
completely empty PostgreSQL volume on 12 October 2026. The fresh deployment
created the schema and default identities, accepted a real text PDF, generated
embeddings, and enforced the document ACL during retrieval.

The RAG integration is ready for team handoff. The eight regression failures
found during this step were subsequently resolved in Step 11; the final backend
suite now passes 47 tests. See `step-11-regression-hardening.md`.

## Start the integrated application

Prerequisites:

- Docker Desktop is running.
- `backend/models/context-intent-v1/` contains the supplied semantic-security
  model files (`config.json`, `model.safetensors`, tokenizer files).
- A Groq API key is available if generated RAG answers are required. Upload,
  ingestion, authorization, and retrieval work without Groq.

From the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace at least `SECRET_KEY` and `POSTGRES_PASSWORD`. Add
`GROQ_API_KEY` for `/api/v1/rag/query`, and add `OPENAI_API_KEY` if the normal
SentinelAI assistant is used. Never commit `.env`.

Start the stack:

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Open:

- Frontend: `http://127.0.0.1:5174`
- API documentation: `http://127.0.0.1:8000/docs`
- Backend health: `http://127.0.0.1:8000/api/v1/health`

Stop without deleting data:

```powershell
docker compose down
```

`docker compose down -v` also deletes PostgreSQL, uploaded PDFs, and the RAG
model cache. Use it only when a fully destructive reset is intended.

## Persistent and external data

| Data | Location in Compose | Purpose |
| --- | --- | --- |
| PostgreSQL | `postgres_data` volume | Users, roles, documents, ACLs, chunks, vectors, conversations, audits |
| Uploaded PDFs | `rag_uploads` volume | Original text-based PDFs used by ingestion |
| Embedding/reranker models | `rag_model_cache` volume | Downloaded local RAG model cache |
| Semantic security model | `backend/models:/app/models:ro` | Separately supplied `context-intent-v1` model |

The backend image uses the official CPU-only PyTorch wheel. This avoids adding
unused CUDA/NVIDIA packages to the Docker image.

## Main RAG API contract

All routes use the normal SentinelAI bearer token. Role IDs come from the
SentinelAI `roles` table; clients must not invent role names or trust roles sent
in a request body.

| Method and route | Who can call it | Purpose |
| --- | --- | --- |
| `GET /api/v1/rag/documents/config` | Administrator | Get role IDs, classifications, upload limits |
| `POST /api/v1/rag/documents` | Administrator | Upload a text PDF with `allowed_roles` |
| `GET /api/v1/rag/documents` | Administrator | List documents and processing status |
| `PATCH /api/v1/rag/documents/{id}/access` | Administrator | Replace a document ACL |
| `DELETE /api/v1/rag/documents/{id}` | Administrator | Deactivate a document |
| `POST /api/v1/rag/documents/{id}/activate` | Administrator | Reactivate a document |
| `DELETE /api/v1/rag/documents/{id}/permanent` | Administrator | Delete PDF, chunks, and vectors permanently |
| `POST /api/v1/rag/retrieval/search` | Authenticated user | Retrieve only role-authorized chunks |
| `POST /api/v1/rag/query` | Authenticated user | Generate a cited Groq answer from authorized chunks |

The integrated workspace also supports RAG mode, persists citations on the
assistant message, and continues to use the SentinelAI security pipeline.

## Verified fresh-deployment evidence

The release check used isolated ports and brand-new named volumes, not the
developer's existing database.

| Check | Result |
| --- | --- |
| Clean backend and frontend image build | Pass |
| PostgreSQL and Redis health checks | Pass |
| Backend health endpoint | Pass |
| pgvector extension | Pass |
| Tables created by startup | 16 |
| Default roles created | 6 |
| Default users created | 6 |
| Administrator login | Pass |
| Employee login | Pass |
| RAG OpenAPI routes | 10 present |
| Frontend TypeScript/Vite production build | Pass |
| Text PDF ingestion | Pass — active, 17 chunks |
| Employee retrieval for Employee-only PDF | Pass — 3 relevant results |
| HR access to Employee-only PDF | Pass — `404`, no existence disclosure |
| Focused RAG acceptance suite | 12 passed |

The fresh smoke test used no Groq key, so live Groq generation was not called in
that disposable environment. Generation behavior and citation formatting are
covered by the focused RAG test suite; perform one provider smoke test after the
recipient supplies their own `GROQ_API_KEY`.

## Baseline blockers found during Step 10

> **Resolved in Step 11:** this section is retained as historical release
> evidence. The final result is 47 passed and 0 failed.

The Step 10 complete backend run reported **38 passed, 8 failed**. None of the
eight failures are in `app/rag` or the role-filtered retrieval tests:

1. Six failures are caused by the existing `context-intent-v1` semantic
   detector behavior or tests that still expect the removed three-regex-detector
   design. The model also marks some benign prompts as dangerous. This needs a
   labeled calibration dataset, threshold review, and updated detector contract
   tests; weakening the production policy just to make tests green would be
   unsafe.
2. One Redis authentication rate-limit test expects a limit of 10 while the
   isolated baseline environment configures 100. The test must inject its own
   limit or derive the expectation from settings.
3. One risk-engine test expects score 60 while the current configured weighting
   formula returns 57. Product owners must decide whether the implementation or
   the older expected score is authoritative.

The integration-owned database-cleanup failure was fixed: isolated auth tests
now remove their test RAG audits/documents and security events before deleting
test users. Production audit foreign keys remain restrictive.

## Handoff acceptance checklist

- [ ] Recipient copies `.env.example` to `.env` and changes all secrets.
- [ ] `backend/models/context-intent-v1/` contains the separate model archive.
- [ ] Recipient runs `docker compose up -d --build` successfully.
- [ ] `/api/v1/health` reports database and Redis as `ok`.
- [ ] Recipient signs in as administrator and opens the Documents page.
- [ ] Administrator uploads a text-based PDF and waits for `active` status.
- [ ] An allowed role retrieves the PDF content.
- [ ] A disallowed role receives no chunks and cannot scope the document ID.
- [ ] Recipient supplies `GROQ_API_KEY` and verifies one cited RAG answer.
- [ ] Default demo passwords/users are removed or changed before deployment.
- [ ] TLS, reverse proxy, backups, secret storage, and log retention are
      configured before any non-local deployment.

## Current scope

The ingestion pipeline intentionally supports native text PDFs only. OCR,
scanned-image PDFs, and image understanding are outside the completed scope.
