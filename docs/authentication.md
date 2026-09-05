# Backend JWT contract

The company backend authenticates users and issues access tokens. The RAG service
does not provide login, registration, password storage, or a token-issuing endpoint.

## Required bearer token

Every protected request includes:

```http
Authorization: Bearer <signed-jwt>
```

The current contract uses HS256 and requires these claims:

```json
{
  "sub": "employee-123",
  "roles": ["hr", "employee"],
  "iss": "company-backend",
  "aud": "secure-rag",
  "iat": 1788524000,
  "exp": 1788524600
}
```

- `sub` is the backend's stable user ID, limited to 128 characters.
- `roles` is a non-empty array containing only `admin`, `hr`, `manager`, or
  `employee`.
- `iss` and `aud` must exactly match the RAG service configuration.
- `iat` and `exp` are NumericDate values. Short-lived tokens are recommended.

The backend and RAG service must receive the same `JWT_SECRET_KEY` from their
secret-management system. Use at least 32 random bytes and never commit the
secret. An asymmetric algorithm and public-key verification are recommended when
the system advances beyond this single-backend deployment.

## Authorization boundary

Roles are accepted only from a successfully verified JWT. The RAG service ignores
role-like request fields and will apply the extracted role set to vector retrieval.

Use `GET /v1/auth/me` during integration to confirm how the RAG service interprets
a backend-issued token.
