"""Tests for the research-paper RAG evaluation calculations."""

import uuid

import pytest

from app.rag.evaluation import EvaluationObservation, evaluate
from app.rag.generation.citations import validate_and_build_citations
from app.rag.generation.llm import GeneratedAnswer, LLMGenerationError
from app.rag.retrieval.retriever import RetrievedChunk


def test_evaluation_report_calculates_retrieval_and_security_metrics() -> None:
    observations = [
        EvaluationObservation(
            case_id="relevant-first",
            expected_document_ids=frozenset({"policy"}),
            returned_document_ids=("policy", "resume"),
            retrieved_chunk_ids=frozenset({"chunk-policy"}),
            cited_chunk_ids=("chunk-policy",),
        ),
        EvaluationObservation(
            case_id="correct-empty",
            expected_document_ids=frozenset(),
            expected_empty=True,
        ),
        EvaluationObservation(
            case_id="role-denied",
            expected_document_ids=frozenset(),
            expected_denied=True,
            status_code=404,
        ),
    ]

    report = evaluate(observations)

    assert report.case_count == 3
    assert report.precision_at_k == 0.75
    assert report.recall_at_k == 1.0
    assert report.mean_reciprocal_rank == 1.0
    assert report.empty_result_accuracy == 1.0
    assert report.authorization_accuracy == 1.0
    assert report.citation_integrity == 1.0


def test_citation_integrity_detects_a_citation_outside_retrieved_context() -> None:
    report = evaluate(
        [
            EvaluationObservation(
                case_id="invalid-citation",
                expected_document_ids=frozenset({"policy"}),
                returned_document_ids=("policy",),
                retrieved_chunk_ids=frozenset({"real-chunk"}),
                cited_chunk_ids=("invented-chunk",),
            )
        ]
    )

    assert report.citation_integrity == 0.0


def test_generation_rejects_a_citation_not_present_in_authorized_context() -> None:
    chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_name="Employee Policy",
        page_number=1,
        content="Employees receive 17 leave days.",
        score=0.9,
    )

    valid = validate_and_build_citations(
        GeneratedAnswer("Employees receive 17 leave days [S1].", ["S1"], True),
        {"S1": chunk},
    )
    assert valid[0].chunk_id == chunk.chunk_id

    with pytest.raises(LLMGenerationError):
        validate_and_build_citations(
            GeneratedAnswer("Unsupported claim [S9].", ["S9"], True),
            {"S1": chunk},
        )
