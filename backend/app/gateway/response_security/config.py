from dataclasses import dataclass

from app.gateway.detectors.result import DetectorStatus
from app.gateway.risk.assessment import RiskSeverity


@dataclass(frozen=True)
class ResponseDetectorConfig:
    detector_id: str
    category: str
    weight: float
    status: DetectorStatus
    score: int
    confidence: int
    severity: RiskSeverity
    patterns: dict[str, str]


RESPONSE_DETECTOR_CONFIGS = {
    "SensitiveDataLeakDetector": ResponseDetectorConfig(
        "RESPONSE_SENSITIVE_DATA_001", "Sensitive Data Leak", 1.4, DetectorStatus.DANGEROUS, 90, 95, RiskSeverity.CRITICAL,
        {
            "openai_api_key": r"\bsk-[A-Za-z0-9_-]{20,}\b",
            "bearer_token": r"\bbearer\s+[A-Za-z0-9._~+/=-]{16,}",
            "jwt": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
            "aws_access_key": r"\bAKIA[0-9A-Z]{16}\b",
            "google_api_key": r"\bAIza[\w-]{30,}\b",
            "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            "password_assignment": r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+",
            "connection_string": r"\b(?:postgresql|mysql|mongodb)://\S+",
            "environment_variable": r"\b(?:API_KEY|SECRET_KEY|DATABASE_URL)\s*=\s*\S+",
        },
    ),
    "PIIDetector": ResponseDetectorConfig(
        "RESPONSE_PII_001", "Personally Identifiable Information", 1.1, DetectorStatus.WARNING, 50, 85, RiskSeverity.HIGH,
        {
            "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            "phone": r"\b(?:\+?\d{1,3}[-. ]?)?(?:\d{3}[-. ]?){2}\d{4}\b",
            "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
            "aadhaar": r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b",
            "passport": r"\b[A-Z][0-9]{7,8}\b",
            "social_security": r"\b\d{3}-\d{2}-\d{4}\b",
            "employee_or_customer_id": r"\b(?:employee|customer)[ _-]?id\s*[:#]?\s*[A-Z0-9-]+",
            "bank_account": r"\b\d{9,18}\b",
        },
    ),
    "ToxicityDetector": ResponseDetectorConfig(
        "RESPONSE_TOXICITY_001", "Toxicity", 1.2, DetectorStatus.DANGEROUS, 70, 80, RiskSeverity.HIGH,
        {
            "violent_threat": r"\b(?:i(?:'m| am) going to kill you|i will kill you|hurt you)\b",
            "harassment": r"\b(?:you are worthless|you should die|i hate you)\b",
            "extreme_profanity": r"\b(?:fuck you|motherfucker)\b",
        },
    ),
    "HallucinationMarkerDetector": ResponseDetectorConfig(
        "RESPONSE_UNCERTAINTY_001", "Uncertainty Marker", 0.6, DetectorStatus.WARNING, 20, 40, RiskSeverity.LOW,
        {
            "i_think": r"\bi think\b",
            "maybe": r"\bmaybe\b",
            "possibly": r"\bpossibly\b",
            "not_sure": r"\bi(?:'m| am) not sure\b",
            "it_appears": r"\bit appears\b",
            "it_seems": r"\bit seems\b",
        },
    ),
}

DEFAULT_RESPONSE_DETECTOR_WEIGHT = 1.0
RESPONSE_SEVERITY_THRESHOLDS = (("CRITICAL", 75), ("HIGH", 50), ("MEDIUM", 25), ("LOW", 0))
