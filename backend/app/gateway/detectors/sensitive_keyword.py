from app.gateway.context import RequestContext
from app.gateway.detectors.base import PromptDetector
from app.gateway.detectors.normalization import normalize_prompt
from app.gateway.detectors.patterns import SENSITIVE_KEYWORDS
from app.gateway.detectors.result import DetectorResult, DetectorStatus


class SensitiveKeywordDetector(PromptDetector):

    # Generic terms that can appear in completely legitimate
    # educational questions.
    EDUCATIONAL_TERMS = {
        "database",
        "internal",
        "credentials",
        "password",
        "api key",
        "secret key",
        "system prompt",
    }

    def analyze(self, context: RequestContext) -> DetectorResult:

        prompt = normalize_prompt(context.prompt)

        intent = context.metadata.get("intent")
        intent_confidence = context.metadata.get(
            "intent_confidence",
            0,
        )

        matches = [
            keyword
            for keyword in SENSITIVE_KEYWORDS
            if keyword in prompt
        ]

        if not matches:
            return DetectorResult(
                self.__class__.__name__,
                DetectorStatus.SAFE,
                0,
                100,
                "No sensitive keyword matched.",
            )

        # ---------------------------------------------------------
        # SEMANTIC CONTEXT GATE
        # ---------------------------------------------------------
        #
        # If the semantic model is highly confident that this is
        # an educational question, generic security terminology
        # should not automatically become a security finding.
        #
        if (
            intent == "safe_educational"
            and intent_confidence >= 90
        ):

            meaningful_matches = [
                keyword
                for keyword in matches
                if keyword not in self.EDUCATIONAL_TERMS
            ]

            if not meaningful_matches:
                return DetectorResult(
                    detector_name=self.__class__.__name__,
                    status=DetectorStatus.SAFE,
                    score=0,
                    confidence=round(intent_confidence),
                    reason=(
                        "Sensitive keywords were present, but "
                        "context/intent indicates a legitimate "
                        "educational request."
                    ),
                    matched_patterns=matches,
                    metadata={
                        "semantic_gate": "safe_educational",
                        "intent": intent,
                        "intent_confidence": intent_confidence,
                    },
                )

            matches = meaningful_matches

        # ---------------------------------------------------------
        # ACTUAL SENSITIVE REQUEST
        # ---------------------------------------------------------

        return DetectorResult(
            detector_name=self.__class__.__name__,
            status=DetectorStatus.WARNING,
            score=50,
            confidence=85,
            reason=(
                "Matched enterprise-sensitive keyword "
                "outside a safe educational context."
            ),
            matched_patterns=matches,
            metadata={
                "intent": intent,
                "intent_confidence": intent_confidence,
            },
        )