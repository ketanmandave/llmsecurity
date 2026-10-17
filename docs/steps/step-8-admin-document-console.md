# Step 8 - Administrator Document Console

## Outcome

Secure RAG document management is now part of the SentinelAI React
administrator console. The separate legacy RAG `/admin` page is not used.

Administrators can:

- upload native-text PDFs;
- choose a sensitivity classification;
- assign one or more dynamic SentinelAI database roles;
- monitor ingestion status;
- replace a document's complete role ACL;
- retry failed or quarantined processing;
- deactivate a document immediately;
- reactivate an inactive document;
- permanently delete its PDF, ACL, chunks, vectors, and findings.

## Frontend location

The administrator sidebar now contains:

```text
Documents -> /documents
```

The route remains protected by the existing SentinelAI administrator route
guard. All API operations also enforce the backend administrator dependency;
the browser is not the security boundary.

## Upload flow

```text
Documents page opens
    -> GET /api/v1/rag/documents/config
       -> dynamic roles, classifications, file limit
    -> administrator selects PDF, name, classification, roles
    -> browser validates extension, size, and non-empty ACL
    -> multipart POST /api/v1/rag/documents
    -> backend revalidates MIME, PDF bytes, structure, text layer, roles
    -> processing status returned
    -> page polls document list while processing
    -> active, quarantined, or failed status displayed
```

Role IDs are serialized in the multipart `allowed_roles` field. The backend
validates those IDs against SentinelAI's `roles` table. Role names are never
hard-coded in the document page.

## Safety and usability

- The page clearly warns that scanned/image-only PDFs are unsupported.
- At least one access role is required.
- The configured maximum upload size is enforced in the browser and backend.
- Permanent deletion requires an explicit browser confirmation explaining all
  data that will be erased.
- Processing documents are refreshed every three seconds.
- Backend parsing or security errors are displayed to the administrator.
- Document roles, classification, file size, page count, and lifecycle status
  are visible in the library.

## Main files

- `frontend/src/pages/DocumentsPage.tsx` - complete document-management page.
- `frontend/src/layouts/ProtectedLayout.tsx` - Documents navigation item.
- `frontend/src/routes/index.tsx` - protected `/documents` route.

The page consumes the backend routes completed in Steps 5 and 6. No additional
authentication or permission implementation was added to the frontend.

## Verification

Frontend verification:

```text
TypeScript compilation: passed
Vite production build: passed
```

Live administrator API lifecycle test:

| Operation | Result |
| --- | --- |
| Load dynamic configuration | 6 roles returned |
| Upload small native-text PDF | accepted as `processing` |
| Secure ingestion | completed as `active` |
| Vector chunks created | 1 |
| Security findings | 0 |
| Deactivate | changed to `inactive` |
| Reactivate | changed to `active` |
| Permanent deletion | document and stored PDF deleted |
| Lookup after deletion | `404 Not Found` |

The temporary verification document was permanently removed from the database,
vector store, upload storage, and local workspace after the test.

The frontend build reports the existing Vite bundle-size advisory only; it is
not a compilation error.

## Run after integration

Rebuild the backend and frontend images so the permanent images contain all
dependencies and source changes:

```powershell
docker compose up -d --build
```

Then sign in through the administrator portal and open:

```text
http://localhost:5174/documents
```

> Step 9 status: integrated retrieval, authorization, lifecycle, citation, and
> research-metric validation is now complete. See
> `docs/steps/step-9-integrated-acceptance-and-evaluation.md`.
