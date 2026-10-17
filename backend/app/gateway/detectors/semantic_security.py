from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from app.gateway.context import RequestContext
from app.gateway.detectors.base import PromptDetector
from app.gateway.detectors.result import DetectorResult, DetectorStatus


MODEL_PATH = (
    Path(__file__).resolve().parents[3]
    / "models"
    / "context-intent-v1"
)


class SemanticSecurityDetector(PromptDetector):
    """
    Single semantic security classifier.

    Understands the contextual meaning and intent of the complete
    prompt and classifies it into a security category.
    """

    _tokenizer = None
    _model = None
    _device = None

    @classmethod
    def _load_model(cls):
        if cls._model is not None:
            return

        cls._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(
            f"[SemanticSecurityDetector] Loading model on {cls._device}..."
        )

        cls._tokenizer = AutoTokenizer.from_pretrained(
            str(MODEL_PATH)
        )

        cls._model = AutoModelForSequenceClassification.from_pretrained(
            str(MODEL_PATH)
        )

        cls._model.to(cls._device)
        cls._model.eval()

        print("[SemanticSecurityDetector] Model loaded successfully.")

    def analyze(self, context: RequestContext) -> DetectorResult:
        self._load_model()

        inputs = self._tokenizer(
            context.prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )

        inputs = {
            key: value.to(self._device)
            for key, value in inputs.items()
        }

        # Some compatible tokenizers emit token_type_ids, but DistilBERT does
        # not accept that argument in forward(). Remove it for this model so
        # the locally supplied classifier can run across tokenizer versions.
        if self._model.config.model_type == "distilbert":
            inputs.pop("token_type_ids", None)

        with torch.no_grad():
            outputs = self._model(**inputs)

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1,
        )[0]

        predicted_id = int(
            torch.argmax(probabilities).item()
        )

        label = self._model.config.id2label[predicted_id]
        confidence = float(
            probabilities[predicted_id].item() * 100
        )

        label = label.lower().replace(" ", "_")

        # Store semantic classification in request context.
        context.metadata["security_intent"] = label
        context.metadata["security_intent_confidence"] = confidence

        # Safe categories
        safe_categories = {
            "safe_educational",
            "general_conversation",
        }

        if label in safe_categories:
            status = DetectorStatus.SAFE
            score = 0
        else:
            status = DetectorStatus.DANGEROUS
            score = confidence

        return DetectorResult(
            detector_name=self.__class__.__name__,
            status=status,
            score=score,
            confidence=confidence,
            reason=(
                f"Semantic security classifier detected "
                f"{label} with {confidence:.2f}% confidence."
            ),
            matched_patterns=[],
            metadata={
                "security_intent": label,
                "security_intent_confidence": confidence,
            },
        )
