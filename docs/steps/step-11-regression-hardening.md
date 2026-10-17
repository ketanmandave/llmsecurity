# Step 11 — Regression Hardening and Green Release Gate

## Outcome

Step 11 resolved every backend regression identified during the Step 10 release
audit without weakening the production RAG ACL or the default semantic-security
pipeline.

Final verification:

- Backend: **47 passed, 0 failed**
- Focused deterministic regression set: **19 passed, 0 failed**
- Frontend TypeScript/Vite production build: **passed**
- Production gateway default: local `SemanticSecurityDetector` remains enabled
- RAG authorization: unchanged and still enforced inside retrieval queries

## Changes

### 1. Testable security gateway

`SentinelAIGateway` now accepts optional prompt, authorization, risk, and policy
stages. Normal application construction supplies none of them, so production
behavior is unchanged. Tests can inject explicit detector evidence and verify a
single concern without depending on an ML prediction.

This prevents authorization, policy, and audit-persistence unit tests from
failing when the semantic model is retrained or recalibrated.

### 2. Tests aligned with the current architecture

The prompt-security contract tests now expect the current single
`SemanticSecurityDetector`, rather than the older three-regex-detector design.
The real model is still exercised with known safe and malicious examples.

Risk tests now assert the active default detector weights and the implemented
score of 57. Rate-limit tests derive the request count from runtime settings
instead of assuming a hard-coded limit of 10.

### 3. Rapid-login JWT collision fixed

Access and refresh tokens now contain a random JWT ID (`jti`). Previously, two
logins for the same user during the same second could produce identical refresh
tokens because all claims were identical. The second database insert then
violated the unique refresh-token constraint and returned HTTP 500.

The new regression test confirms that access and refresh tokens issued in the
same second are different and contain different `jti` claims.

## Semantic-model calibration finding

The local model was evaluated against the exact prompts involved in the failed
tests. It correctly classified `Hello` and `Explain PostgreSQL` as safe and a
DAN jailbreak as dangerous. It also produced these false positives:

- `Summarize the quarterly meeting agenda.` → prompt injection, 58.76%
- `Contact analyst@example.com. I think this is safe.` → credential access,
  84.82%

No production threshold was weakened to make tests pass. The proper follow-up
is to build a labeled validation set covering benign workplace prompts, prompt
injection, jailbreaks, credential access, and ambiguous examples. Choose model
thresholds from measured precision/recall and business risk rather than two
hand-selected prompts.

## Commands used for the final gate

```powershell
docker compose -p sentinel-baseline -f docker-compose.baseline.yml build sentinel-backend
docker compose -p sentinel-baseline -f docker-compose.baseline.yml up -d --no-deps sentinel-backend
docker exec sentinel-baseline-backend python -m pytest -q
docker exec sentinel-baseline-frontend npm run build
```

## Final handoff status

The integrated codebase has a green automated backend suite and a successful
frontend production compile. Provider smoke tests still require the recipient's
own OpenAI/Groq credentials, and model-quality claims must be supported by the
future labeled calibration evaluation.
