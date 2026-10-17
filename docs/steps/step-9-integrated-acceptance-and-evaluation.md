# Step 9 - Integrated Acceptance and RAG Evaluation

## Outcome

The combined SentinelAI and Secure RAG system now has a repeatable evaluation
layer and has passed a live two-role security smoke test.

This step validates the most important research and security claims without
leaving test documents or vectors in the application.

## Metrics implemented

`backend/app/rag/evaluation/metrics.py` calculates:

| Metric | Meaning |
| --- | --- |
| Precision@K | Fraction of returned chunks belonging to expected documents |
| Recall@K | Fraction of expected documents represented in the result set |
| MRR | Reciprocal rank of the first relevant chunk |
| Empty-result accuracy | Unrelated questions correctly returning no chunks |
| Authorization accuracy | Forbidden document scopes correctly returning `403` or `404` |
| Citation integrity | Citations referencing chunks actually supplied to generation |

The metrics return values from `0.0` to `1.0` and are deterministic for a
labelled observation set.

## Running an evaluation dataset

An example dataset is available at:

```text
docs/evaluation/rag-evaluation-dataset.example.json
```

From the backend directory run:

```powershell
python scripts/evaluate_rag_dataset.py ..\docs\evaluation\rag-evaluation-dataset.example.json
```

To save the report:

```powershell
python scripts/evaluate_rag_dataset.py `
  ..\docs\evaluation\rag-evaluation-dataset.example.json `
  --output ..\docs\evaluation\rag-evaluation-report.json
```

The script consumes observed API results. It does not invent expected labels;
the research team must define relevant documents and expected empty/denied
cases before running the experiment.

## Live security dataset

Two temporary native-text PDFs were created:

- Employee-only `ZEUSLEAVE` policy.
- HR-only `ORIONPAYROLL` procedure.

Each contained a unique term so relevance and authorization could be evaluated
independently.

Observed results:

| Case | Expected | Result |
| --- | --- | --- |
| Employee asks about `ZEUSLEAVE` | Employee document first | Passed |
| Employee scopes HR document | Denied without revealing existence | `404` |
| HR scopes Employee document | Denied without revealing existence | `404` |
| Employee asks unrelated Mars-cake question | No result | Empty result |
| Admin deactivates Employee document | Immediately unavailable | `404` |
| Admin reactivates Employee document | Available again | `200` |

Smoke-test metrics:

```text
Precision@K            1.00
Recall@K               1.00
MRR                    1.00
Empty-result accuracy  1.00
Authorization accuracy 1.00
```

Machine-readable results are stored in
`docs/evaluation/step-9-evaluation-results.json`.

## Citation validation

Automated tests prove that:

- a valid citation maps to the exact retrieved chunk;
- a grounded answer without citations is rejected;
- a citation ID absent from the supplied authorized context is rejected;
- the evaluation metric detects citations outside the retrieved chunk set.

Semantic citation accuracy—whether the cited text truly supports every claim—
still needs a human-labelled answer set or a separately validated judge. It
must not be claimed solely from source-ID integrity.

## Automated verification

The complete focused Secure RAG suite passed:

```text
12 passed
```

The warnings reported by pytest are existing framework deprecation notices;
there were no test failures.

## Cleanup

Both temporary documents were permanently deleted after testing. Verification
confirmed removal of:

- document rows;
- allowed-role rows;
- chunks and embeddings;
- security findings;
- uploaded PDF files;
- temporary local test PDFs.

No user document was modified.

## Research-paper caution

The perfect smoke-test scores demonstrate that the security and evaluation
pipeline behaves correctly on a deliberately small controlled dataset. They
are not statistically meaningful accuracy results.

Before publishing final accuracy claims, create a larger labelled dataset with:

- questions for every department and role;
- multiple relevant documents per question;
- semantically similar but irrelevant documents;
- paraphrased and ambiguous questions;
- unrelated questions;
- explicitly unauthorized document scopes;
- human-verified answers and supporting citation chunks.

Report the dataset size, role distribution, `K`, model versions, thresholds,
and test environment with the final metrics.

## Next step

Step 10 should prepare production deployment and project handoff: clean-image
rebuild, fresh-database startup, full regression suite, environment/secret
checklist, backup guidance, API handoff, and final release checklist.
