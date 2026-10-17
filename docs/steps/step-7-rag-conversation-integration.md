# Step 7 - RAG Conversations, Security, and Citations

## Outcome

The employee workspace now supports two explicit message modes:

- `assistant` - the existing general SentinelAI/OpenAI flow.
- `rag` - role-authorized company-document retrieval and grounded Groq
  generation.

The frontend never supplies a user role. SentinelAI derives the active user and
database role from its access token before the RAG workflow starts.

## End-to-end RAG conversation flow

```text
Employee selects Company Knowledge
    -> POST /api/v1/workspace/conversations/{id}/messages
    -> SentinelAI authenticates active user
    -> authorization rules
    -> prompt detectors
    -> risk engine
    -> policy engine
       -> blocked: safe blocked response; RAG is never called
       -> allowed/warned: call Secure RAG
    -> role-ID-filtered retrieval
    -> retrieved-context security guard
    -> Groq grounded generation
    -> RAG output guard and citation validation
    -> SentinelAI response-security analysis
    -> persist security event
    -> persist assistant answer and citations
    -> render answer and source cards in employee workspace
```

One server-generated request ID is shared by the user message, assistant
message, SentinelAI security event, and RAG audit event.

## Workspace API

The existing endpoint remains:

```text
POST /api/v1/workspace/conversations/{conversation_id}/messages
```

General assistant request:

```json
{
  "content": "Explain least privilege.",
  "mode": "assistant"
}
```

Company-knowledge request:

```json
{
  "content": "What is the employee leave policy?",
  "mode": "rag",
  "document_ids": null
}
```

`document_ids` is optional and is valid only in `rag` mode. If supplied, every
document is checked against the authenticated user's role before retrieval.
RAG questions are limited to 4,000 characters.

Each returned and subsequently reloaded message now contains:

- `mode`
- `request_id`
- `citations`
- `grounded`
- `model`

## Persistence changes

The `messages` table received additive columns:

| Column | Purpose |
| --- | --- |
| `mode` | Records `assistant` or `rag` |
| `citations` | Validated source metadata as JSON |
| `request_id` | Correlates messages and security/audit records |
| `grounded` | Indicates whether document evidence supported the answer |
| `model` | Records the generation model |

Existing messages are preserved and receive `mode = 'assistant'` and an empty
citation list. Startup applies the additive columns and request-ID index.

## Main implementation files

- `backend/app/api/routes/workspace.py` - selects assistant or RAG execution.
- `backend/app/gateway/service.py` - adds an asynchronous provider path wrapped
  by the existing SentinelAI security pipeline.
- `backend/app/rag/integration/conversation.py` - invokes the secured RAG query
  workflow with the shared request ID.
- `backend/app/models/conversation.py` - stores mode, citations, grounding, model,
  and correlation ID.
- `backend/app/schemas/workspace.py` - validates mode-specific requests and
  serializes citation metadata.
- `backend/app/database/init_db.py` - applies additive message columns.
- `frontend/src/pages/EmployeeWorkspacePage.tsx` - mode selector and citation
  cards.

## Verification

Focused backend integration tests:

```text
9 passed
```

Verified behavior:

- A safe RAG provider response passes through SentinelAI response security.
- A policy-blocked prompt does not call the RAG provider.
- Assistant mode rejects `document_ids`.
- Message models contain all RAG persistence fields.
- The live workspace stored both user and assistant messages in `rag` mode.
- User and assistant records shared the same request ID.
- A blocked RAG conversation returned no citations.
- Reloading the conversation preserved the RAG mode.
- Backend, database, and Redis health remained healthy.
- Frontend TypeScript and Vite production build passed.

The Vite build reports only its existing bundle-size advisory; it does not
report a compilation failure.

## Runtime requirement

For real grounded answers, configure `GROQ_API_KEY`, upload and successfully
process at least one text-based PDF, and grant the current user's database role
access to it. The first embedding/reranking operation may initialize the local
models and therefore take longer than later requests.

After source changes, rebuild the application image:

```powershell
docker compose up -d --build
```

> Step 8 status: the SentinelAI administrator document console is now complete.
> See `docs/steps/step-8-admin-document-console.md`.
