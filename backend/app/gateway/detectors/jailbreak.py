import re

from app.gateway.context import RequestContext
from app.gateway.detectors.base import PromptDetector
from app.gateway.detectors.normalization import normalize_prompt
from app.gateway.detectors.patterns import JAILBREAK_PATTERNS
from app.gateway.detectors.result import DetectorResult, DetectorStatus


class JailbreakDetector(PromptDetector):
    def analyze(self, context: RequestContext) -> DetectorResult:
        prompt = normalize_prompt(context.prompt)
        matches = [pattern for pattern in JAILBREAK_PATTERNS if re.search(rf"\b{re.escape(pattern)}\b", prompt)]
        if matches:
            return DetectorResult(
                detector_name=self.__class__.__name__,
                status=DetectorStatus.DANGEROUS,
                score=85,
                confidence=90,
                reason="Matched common jailbreak pattern.",
                matched_patterns=matches,
            )
        return DetectorResult(self.__class__.__name__, DetectorStatus.SAFE, 0, 100, "No jailbreak pattern matched.")
