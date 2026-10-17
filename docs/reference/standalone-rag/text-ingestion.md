# Native-text PDF ingestion

The service intentionally accepts only PDFs that contain an extractable text
layer. OCR, image understanding, chart description, and special table extraction
are outside the current project scope.

## Upload validation

Before a document row is created, the API validates the filename and MIME type,
PDF magic bytes, upload size, parseability, encryption status, page limit, roles,
and the presence of extractable text. A scanned or image-only PDF returns HTTP 422
with:

```text
PDF contains no extractable text; only text-based PDFs are supported
```

## Processing flow

```text
PDF -> native text extraction -> PII/injection scan -> chunks
    -> local embeddings -> PostgreSQL/pgvector
```

Each chunk stores its one-based page number, `content_type=text`,
`source_type=pymupdf`, hash, token count, scan status, and vector. Retrieval applies
the authenticated user's roles, active document status, approved chunk status,
optional document IDs, and `content_type=text` inside the database query.

The last condition also prevents legacy OCR, table, or vision chunks from being
returned if the database contains data created by an older build. Existing files
are not deleted automatically; administrators can deactivate or permanently
delete them from the dashboard.

Tables are searchable only to the extent that their words exist in the PDF text
layer. Images, diagrams, handwriting, and scanned text are not interpreted.
