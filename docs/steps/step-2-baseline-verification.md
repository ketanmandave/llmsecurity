# SentinelAI Step 2 Baseline Verification

Date: 2026-10-12

## Outcome

The independent SentinelAI stack starts and its main browser/API flows work, but the backend test suite is not fully green. Do not begin the RAG merge until the seven remaining test failures are resolved or intentionally re-baselined.

## Isolated baseline

The baseline uses separate resources so it does not conflict with the existing Secure RAG stack:

- Frontend: `http://127.0.0.1:15174`
- Backend: `http://127.0.0.1:18000`
- PostgreSQL host port: `15433`
- Redis host port: `16380`
- Compose file: `docker-compose.baseline.yml`
- Environment file: `backend/.env.baseline`

## Verification results

| Check | Result | Evidence |
| --- | --- | --- |
| Fresh isolated PostgreSQL | PASS | Dedicated `sentinel_baseline_postgres` volume and `sentinel-baseline-db` container |
| Redis | PASS | `sentinel-baseline-redis` is healthy |
| Backend environment | PASS | Isolated database, Redis, CORS, and development settings loaded |
| Backend dependencies | PASS | Backend image built successfully; PyTorch, Transformers, and Safetensors are installed |
| Backend startup | PASS | `sentinel-baseline-backend` is healthy on port `18000` |
| `init_db()` schema | PASS | 11 public tables created |
| Default roles | PASS | 6 roles created: Employee, HR, Manager, Payroll Administrator, Security Analyst, SentinelAI Administrator |
| Default users | PASS | 6 matching demo users created |
| Health endpoint | PASS | Backend, database, and Redis all report `ok` |
| Employee API login | PASS | Seeded employee authenticated and `/auth/me` returned role Employee |
| Conversation APIs | PASS | Conversation create/list completed successfully |
| Security pipeline | PASS with caveat | Malicious prompt was blocked and recorded; model behavior tests still have mismatches listed below |
| Administrator APIs | PASS | Administrator authenticated; dashboard metrics and user administration endpoints returned successfully |
| Frontend startup | PASS | Frontend serves HTTP 200 on port `15174` |
| Frontend production build | PASS | TypeScript and Vite build completed successfully |
| Employee browser login | PASS | Browser reached `/employee` and displayed Employee workspace |
| Administrator browser login | PASS | Browser reached `/dashboard` and displayed metrics/navigation |
| Backend tests | FAIL | 27 passed, 7 failed |

## Fixes made during verification

1. Removed `token_type_ids` before DistilBERT inference because this model's `forward()` does not accept that tokenizer field.
2. Mounted the separately supplied `backend/models` directory into the baseline backend container.
3. Mounted `backend/tests` into the verification container so tests actually run.
4. Configured the frontend to call the isolated backend on port `18000`.
5. Allowed both `localhost:15174` and `127.0.0.1:15174` in baseline CORS settings.

## Remaining backend failures

Test command:

```powershell
docker exec -e PYTHONPATH=/app sentinel-baseline-backend pytest -q --tb=short
```

Current result: **27 passed, 7 failed**.

Failure groups:

- Semantic classifier expectations: safe/test prompts are sometimes classified as dangerous, affecting authorization, policy, prompt-pipeline, and security-event tests.
- Redis rate limiting: the eleventh failed-login request returns `401` instead of the expected `429`.
- Risk scoring: implementation returns `57`; the test expects `60`.

These are SentinelAI baseline issues and are unrelated to the Secure RAG code. They should be fixed before integration so regressions introduced by the merge can be distinguished from pre-existing failures.

## Commands

Start or rebuild the isolated baseline:

```powershell
cd C:\Users\ketan\OneDrive\Desktop\llmSecurity
docker compose -p sentinel-baseline -f docker-compose.baseline.yml up -d --build
```

Check status:

```powershell
docker compose -p sentinel-baseline -f docker-compose.baseline.yml ps
Invoke-RestMethod http://127.0.0.1:18000/api/v1/health
```

Stop the isolated baseline without deleting its database:

```powershell
docker compose -p sentinel-baseline -f docker-compose.baseline.yml stop
```
