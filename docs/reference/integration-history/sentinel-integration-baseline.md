# SentinelAI and Secure RAG integration baseline

Recorded on 11 October 2026 before integration changes.

> Historical record: the imported `sentinel-ai-college-main/` directory was
> promoted to the repository root after Step 11. Paths and fingerprints below
> describe the pre-integration snapshot and are intentionally not current.

## Preservation state

- Integration branch: `codex/sentinel-rag-integration`
- Root repository starting commit: `da84225d62e5cdfc318e2e350e238ae707d4c347`
- The root working tree already contains the completed Secure RAG work and is intentionally not reset.
- `sentinel-ai-college-main/` is an imported source folder without nested Git metadata.
- No source files have been moved, deleted, or overwritten during this preservation step.
- No commit was created because the existing working tree contains user-owned changes that must remain reviewable.

## Secret and generated-file protection

The following paths are ignored and must stay outside version control:

- Root and application `.env` files
- Python virtual environments
- Frontend `node_modules`
- SentinelAI `backend/models/`
- RAG model caches and uploaded documents

No environment-variable values, passwords, API keys, JWT secrets, or model contents are recorded in this baseline.

## Semantic model prerequisites

`sentinel-ai-college-main/backend/requirements.txt` already contains:

- `torch==2.6.0`
- `transformers==4.48.3`
- `safetensors==0.5.3`

The separately supplied `context-intent-v1` archive must be extracted under
`sentinel-ai-college-main/backend/models/context-intent-v1/` before the semantic detector is tested.

## Baseline fingerprints

These SHA-256 hashes identify the source files inspected before integration:

| File | SHA-256 |
| --- | --- |
| `requirements.txt` | `985E76A1B7A1BC72FE04ACB91553DB53CD3F989FC841DDBDA522DD5769C5149C` |
| `sentinel-ai-college-main/backend/requirements.txt` | `D38637036851C1C6005457957AF9280FEA7F6B283910475811DDCACEB4354523` |
| `sentinel-ai-college-main/backend/app/main.py` | `D0203A746A5E3B7E0429D8333EE8BD89AA2CF8937F53775162B6A9099A51A6EC` |
| `sentinel-ai-college-main/docker-compose.yml` | `226536BF9B47AFA6E0B1F6A7B6BE4EBA9A1E34666FB8DA9D7DF5F6EAEC3D1F38` |

## Next gate

Step 2 must verify SentinelAI independently against a fresh PostgreSQL database before any RAG code is copied or connected. The check must cover startup initialization, default roles and users, Redis connectivity, authentication, conversations, gateway behavior, automated tests, and frontend startup.

Step 3's agreed target contract is now recorded in
`docs/steps/step-3-rag-integration-contract.md`. It makes
SentinelAI authoritative for users, tokens, and roles; RAG authorization will
use the server-resolved SentinelAI role and apply it inside document retrieval.
