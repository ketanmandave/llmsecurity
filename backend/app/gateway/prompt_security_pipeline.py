import json
import logging

from app.gateway.context import RequestContext
from app.gateway.detectors.base import PromptDetector
from app.gateway.detectors.semantic_security import SemanticSecurityDetector

logger = logging.getLogger("sentinelai.gateway.prompt_security")


class PromptSecurityPipeline:
    """
    Semantic security pipeline.

    A single transformer model analyzes the complete prompt,
    understands its context and intent, and classifies it into
    a security category.
    """

    def __init__(
        self,
        detectors: list[PromptDetector] | None = None,
    ) -> None:
        self.detectors = detectors or [
            SemanticSecurityDetector(),
        ]

    def process(self, context: RequestContext) -> RequestContext:
        for detector in self.detectors:
            result = detector.analyze(context)

            context.detector_results.append(result)

            logger.info(
                json.dumps({
                    "event": "prompt_security_detector_completed",
                    "request_id": context.request_id,
                    "conversation_id": context.conversation_id,
                    "user_id": context.user_id,
                    "detector": result.detector_name,
                    "status": result.status.value,
                })
            )

        return context