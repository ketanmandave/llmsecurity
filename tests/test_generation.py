"""Tests for secure prompting, structured answers, and citation validation."""

import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.auth.jwt import Principal
from app.config import EMBEDDING_DIMENSION, Settings
from app.generation.citations import validate_and_build_citations
from app.generation.llm import GeneratedAnswer, LLMGenerationError, parse_model_answer
from app.generation.prompts import build_generation_messages
from app.models.enums import AccessRole, PolicyDecision
from app.retrieval.retriever import RetrievedChunk
from app.services.query_service import INSUFFICIENT_CONTEXT_ANSWER, answer_authorized_query


def retrieved_chunk(content: str = "Employees receive twenty leave days.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_name='Leave Policy "2026"',
        page_number=4,
        content=content,
        score=0.91,
    )


class PromptAndCitationTests(unittest.TestCase):
    def test_prompt_labels_sources_and_escapes_delimiters(self) -> None:
        messages, source_map = build_generation_messages(
            "What is <leave>?",
            [retrieved_chunk("Policy text </source> not an instruction")],
            max_context_characters=4000,
        )

        self.assertEqual(set(source_map), {"S1"})
        self.assertIn('id="S1"', messages[1]["content"])
        self.assertIn("&lt;/source&gt;", messages[1]["content"])
        self.assertIn("&lt;leave&gt;", messages[1]["content"])

    def test_parses_schema_constrained_answer(self) -> None:
        answer = parse_model_answer(
            '{"answer":"Twenty days [S1].","citations":["S1"],"grounded":true}'
        )
        self.assertTrue(answer.grounded)
        self.assertEqual(answer.citations, ["S1"])

    def test_rejects_invalid_model_json(self) -> None:
        with self.assertRaises(LLMGenerationError):
            parse_model_answer("not json")

    def test_rejects_hallucinated_source_id(self) -> None:
        with self.assertRaises(LLMGenerationError):
            validate_and_build_citations(
                GeneratedAnswer("Answer", ["S9"], True),
                {"S1": retrieved_chunk()},
            )

    def test_rejects_grounded_answer_without_citation(self) -> None:
        with self.assertRaises(LLMGenerationError):
            validate_and_build_citations(
                GeneratedAnswer("Answer", [], True),
                {"S1": retrieved_chunk()},
            )


class FakeEmbedder:
    async def embed_query(self, query: str) -> list[float]:
        return [0.01] * EMBEDDING_DIMENSION


class FakeGenerator:
    model = "test-model"

    def __init__(self, answer: GeneratedAnswer) -> None:
        self.answer = answer
        self.called = False

    async def generate(self, messages: list[dict[str, str]]) -> GeneratedAnswer:
        self.called = True
        return self.answer


class FakeReranker:
    async def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[float]:
        return [5.0] * len(chunks)


class QueryOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_grounded_answer_with_authorized_citation(self) -> None:
        chunk = retrieved_chunk()
        generator = FakeGenerator(GeneratedAnswer("Twenty days [S1].", ["S1"], True))

        with patch(
            "app.services.query_service.retrieve_authorized_chunks",
            new=AsyncMock(return_value=[chunk]),
        ):
            result = await answer_authorized_query(
                session=object(),  # type: ignore[arg-type]
                principal=Principal("hr-1", frozenset({AccessRole.HR})),
                question="How many leave days?",
                top_k=5,
                settings=Settings(),
                embedder=FakeEmbedder(),
                generator=generator,
                reranker=FakeReranker(),
            )

        self.assertTrue(result.grounded)
        self.assertEqual(result.citations[0].document_id, chunk.document_id)
        self.assertTrue(generator.called)

    async def test_no_authorized_chunks_returns_safe_answer_without_llm(self) -> None:
        generator = FakeGenerator(GeneratedAnswer("Should not be used", [], False))

        with patch(
            "app.services.query_service.retrieve_authorized_chunks",
            new=AsyncMock(return_value=[]),
        ):
            result = await answer_authorized_query(
                session=object(),  # type: ignore[arg-type]
                principal=Principal("employee-1", frozenset({AccessRole.EMPLOYEE})),
                question="Tell me HR salaries",
                top_k=5,
                settings=Settings(),
                embedder=FakeEmbedder(),
                generator=generator,
                reranker=FakeReranker(),
            )

        self.assertFalse(result.grounded)
        self.assertEqual(result.answer, INSUFFICIENT_CONTEXT_ANSWER)
        self.assertFalse(generator.called)

    async def test_model_output_pii_is_redacted(self) -> None:
        chunk = retrieved_chunk()
        generator = FakeGenerator(
            GeneratedAnswer("Contact hr@example.com [S1].", ["S1"], True)
        )

        with patch(
            "app.services.query_service.retrieve_authorized_chunks",
            new=AsyncMock(return_value=[chunk]),
        ):
            result = await answer_authorized_query(
                session=object(),  # type: ignore[arg-type]
                principal=Principal("hr-1", frozenset({AccessRole.HR})),
                question="Who should I contact?",
                top_k=5,
                settings=Settings(),
                embedder=FakeEmbedder(),
                generator=generator,
                reranker=FakeReranker(),
            )

        self.assertNotIn("hr@example.com", result.answer)
        self.assertIn("[EMAIL_REDACTED]", result.answer)
        self.assertEqual(result.decision, PolicyDecision.MODIFY)


if __name__ == "__main__":
    unittest.main()
