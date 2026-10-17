# SentinelAI College with Secure Role-Aware RAG

This repository contains one integrated application. SentinelAI owns users,
roles, authentication, conversations, and the security gateway. Secure RAG is
implemented as the `app.rag` backend module and applies document-role ACLs
inside vector retrieval.

## Repository layout

```text
llmSecurity/
├── backend/
│   ├── app/                  FastAPI application
│   │   ├── api/              SentinelAI HTTP controllers
│   │   ├── gateway/          authorization and security pipeline
│   │   ├── models/           shared SentinelAI database models
│   │   └── rag/              ingestion, ACL retrieval, generation, citations
│   ├── ml/                   semantic-model dataset tooling
│   ├── models/               local context-intent-v1 archive (ignored)
│   ├── scripts/              backend evaluation utilities
│   ├── tests/                complete backend test suite
│   └── requirements.txt
├── frontend/                 React/Vite user and administrator application
├── docker/                   backend and frontend Dockerfiles
├── docs/
│   ├── architecture/         architecture flow and figures
│   ├── evaluation/           RAG evaluation inputs and results
│   ├── handoff/              integration and recipient guides
│   ├── research/             research/viva material
│   ├── reference/            archived standalone-RAG references
│   └── steps/                implementation history, Steps 2–11
├── samples/                  safe test PDFs
├── docker-compose.yml        normal integrated stack
└── docker-compose.baseline.yml  isolated verification stack
```

There is intentionally no second root-level Python `app`. Run Python commands
from `backend/` so imports such as `from app.models...` resolve to the single
authoritative package.

## Start the application

1. Ensure Docker Desktop is running.
2. Confirm `backend/models/context-intent-v1/` contains the separately supplied
   semantic model.
3. Copy `.env.example` to `.env` and configure secrets/provider keys.
4. Start the integrated stack.

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

- Frontend: `http://127.0.0.1:5174`
- API documentation: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`

## Development checks

Backend:

```powershell
cd backend
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm install
npm run build
```

The verified Docker acceptance workflow is documented in
`docs/steps/step-11-regression-hardening.md`.

## Scope

- Native text PDFs only; OCR and image understanding are intentionally absent.
- Roles are resolved from authenticated SentinelAI users, never trusted from a
  query request.
- Upload, ACL management, deactivate/reactivate, and permanent deletion are
  administrator operations.
- Retrieval works without Groq; generated cited answers require `GROQ_API_KEY`.


## docker compose up -d --build
## Invoke-RestMethod http://127.0.0.1:8000/api/v1/health