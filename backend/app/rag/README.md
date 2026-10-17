# Secure RAG migration boundary

This package contains the Secure RAG runtime code moved into SentinelAI during
Step 4. All internal imports are namespaced under `app.rag` to prevent
collisions with SentinelAI's existing gateway, models, security, and services.

The package is wired into `app.main` under `/api/v1/rag`. The remaining
integration steps must:

1. connect RAG responses to SentinelAI response security and conversations;
2. add the SentinelAI React document-management views.

`app.rag.auth` now adapts SentinelAI's already-authenticated active user and
database role. It does not decode or issue a second RAG JWT.

Document ACLs reference SentinelAI `roles.id`, uploads reference
SentinelAI `users.id`, and all RAG models share SentinelAI's SQLAlchemy base.

The standalone RAG static administrator page was not copied. Document
management will be implemented in the SentinelAI React administrator console.

