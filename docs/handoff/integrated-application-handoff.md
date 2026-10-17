# Integrated application handoff

## Start from a new machine

1. Install Docker Desktop and Git.
2. Place the separately supplied model files directly in
   `backend/models/context-intent-v1/`.
3. Copy `.env.example` to `.env` and configure strong secrets and provider keys.
4. From the repository root run:

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Open the frontend at `http://127.0.0.1:5174` and Swagger at
`http://127.0.0.1:8000/docs`.

## Backend integration rule

The receiving team should call the integrated FastAPI API; it should not import
RAG internals from another service. Send the normal SentinelAI JWT:

```http
Authorization: Bearer <sentinel-access-token>
```

Main routes:

| Route | Purpose |
| --- | --- |
| `GET /api/v1/rag/documents/config` | Administrator upload roles and limits |
| `POST /api/v1/rag/documents` | Upload a text PDF and assign role IDs |
| `GET /api/v1/rag/documents` | Administrator document library |
| `PATCH /api/v1/rag/documents/{id}/access` | Replace document ACL |
| `DELETE /api/v1/rag/documents/{id}` | Deactivate document |
| `POST /api/v1/rag/documents/{id}/activate` | Reactivate document |
| `DELETE /api/v1/rag/documents/{id}/permanent` | Delete PDF and vectors |
| `POST /api/v1/rag/retrieval/search` | Authorized retrieval without generation |
| `POST /api/v1/rag/query` | Generated answer with validated citations |

The frontend normally uses the workspace conversation endpoint with `mode` set
to `rag`, which adds message persistence and the complete security gateway.

## Data that must be preserved

- PostgreSQL Compose volume: identities, ACLs, chunks, vectors, conversations,
  and audit records.
- `rag_uploads` volume: original PDFs.
- `rag_model_cache` volume: downloaded embedding and reranker models.
- `backend/models/context-intent-v1`: separately distributed semantic model.
- Local `.env`: secrets; never commit or send it through source control.

## Acceptance checklist

- Health reports database and Redis as `ok`.
- Administrator can upload a native-text PDF.
- The document becomes active and creates chunks.
- An allowed role retrieves it.
- A disallowed role receives no results and cannot scope its document ID.
- Groq generation returns citations when `GROQ_API_KEY` is configured.
- Deactivate, reactivate, and permanent deletion work from the Documents page.

Historical standalone endpoints under `/v1` are archived in
`docs/reference/standalone-rag` and must not be used for this integrated build.
