# Integrated SentinelAI and Secure RAG architecture

## Ownership boundaries

SentinelAI is the host application. It owns authentication, users, roles,
conversations, the security gateway, administration, and the React frontend.
Secure RAG is not a second service or second `app` package: it is the
`backend/app/rag` module inside the same FastAPI process.

```text
Browser (React/Vite)
        |
        v
FastAPI /api/v1
  |-- auth, users, roles, workspace, security events
  |-- SentinelAI gateway
  |     authorization -> semantic detector -> risk -> policy -> response guard
  |
  `-- /rag
        |-- administrator document and ACL management
        |-- native-text PDF ingestion
        |-- role-filtered hybrid retrieval
        `-- Groq generation with validated citations
                |
                v
PostgreSQL + pgvector          Redis
users/roles/documents/ACLs     sessions and rate limits
chunks/embeddings/audits
```

## Document ingestion flow

1. An authenticated SentinelAI administrator opens the Documents page.
2. The frontend reads `GET /api/v1/rag/documents/config` for real role IDs and
   upload constraints.
3. It posts the PDF, name, classification, and role IDs to
   `POST /api/v1/rag/documents`.
4. `backend/app/rag/api/documents.py` verifies administrator permission and
   calls `backend/app/rag/services/document_service.py`.
5. The ingestion pipeline validates a native-text PDF, extracts text with
   PyMuPDF, scans it, creates overlapping chunks, embeds approved chunks, and
   stores them in PostgreSQL/pgvector.
6. The document becomes `active` only after indexing succeeds.

## Query flow

1. SentinelAI authenticates the bearer token and resolves the user and role
   from the shared database.
2. Workspace RAG mode enters the same SentinelAI gateway used by normal chat.
3. Input security, authorization, risk, and policy execute before retrieval.
4. `backend/app/rag/retrieval/retriever.py` joins document ACL rows and applies
   the authenticated role IDs inside SQL.
5. Vector, lexical, title, and reranker signals select the final chunks.
6. Groq `openai/gpt-oss-120b` receives only authorized context.
7. Citation validation and response security run before the answer is returned
   and persisted in the conversation.

## Important source locations

| Concern | Location |
| --- | --- |
| FastAPI entry point | `backend/app/main.py` |
| Identity and roles | `backend/app/auth`, `backend/app/models` |
| Security gateway | `backend/app/gateway` |
| RAG routes | `backend/app/rag/api` |
| PDF ingestion | `backend/app/rag/ingestion` |
| Authorized retrieval | `backend/app/rag/retrieval` |
| Generation and citations | `backend/app/rag/generation` |
| Shared database initialization | `backend/app/database/init_db.py` |
| Administrator document UI | `frontend/src/pages/DocumentsPage.tsx` |
| Employee RAG chat | `frontend/src/pages/EmployeeWorkspacePage.tsx` |

## Security invariant

Document roles sent during upload are administrator-managed ACL data. Roles in
query bodies are never trusted. Retrieval uses role IDs resolved server-side
from the authenticated SentinelAI user, and unauthorized explicit document IDs
return `404` to avoid disclosing document existence.
