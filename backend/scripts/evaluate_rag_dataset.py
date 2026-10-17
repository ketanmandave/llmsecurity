"""Calculate Secure RAG research metrics from labelled observation JSON."""

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.rag.evaluation import EvaluationObservation, evaluate


def load_observations(path: Path) -> list[EvaluationObservation]:
    """Validate and convert a JSON observation list into metric inputs."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Evaluation dataset must be a non-empty JSON array")
    return [
        EvaluationObservation(
            case_id=str(item["case_id"]),
            expected_document_ids=frozenset(item.get("expected_document_ids", [])),
            returned_document_ids=tuple(item.get("returned_document_ids", [])),
            retrieved_chunk_ids=frozenset(item.get("retrieved_chunk_ids", [])),
            cited_chunk_ids=tuple(item.get("cited_chunk_ids", [])),
            expected_empty=bool(item.get("expected_empty", False)),
            expected_denied=bool(item.get("expected_denied", False)),
            status_code=int(item.get("status_code", 200)),
        )
        for item in payload
    ]


def main() -> None:
    """Print a reproducible JSON metric report for the supplied observations."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Path to observation JSON")
    parser.add_argument("--output", type=Path, help="Optional report JSON path")
    arguments = parser.parse_args()
    report = evaluate(load_observations(arguments.dataset)).to_dict()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if arguments.output:
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
