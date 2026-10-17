from abc import ABC, abstractmethod

from app.gateway.context import RequestContext
from app.gateway.detectors.result import DetectorResult


class PromptDetector(ABC):
    @abstractmethod
    def analyze(self, context: RequestContext) -> DetectorResult:
        """Analyze a request context without modifying it."""
