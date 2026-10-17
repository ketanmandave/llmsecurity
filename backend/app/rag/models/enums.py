"""Controlled values persisted by the RAG database."""

from enum import Enum


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Persist string enum values rather than uppercase Python member names."""

    return [str(member.value) for member in enum_class]


class Classification(str, Enum):
    """Administrative sensitivity label attached to an uploaded document."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentStatus(str, Enum):
    """Lifecycle states controlling processing and retrieval eligibility."""

    PROCESSING = "processing"
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    FAILED = "failed"
    INACTIVE = "inactive"


class SecurityStatus(str, Enum):
    """Approval state determining whether a chunk may be retrieved."""

    PENDING = "pending"
    APPROVED = "approved"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class PolicyDecision(str, Enum):
    """Ordered security outcomes recorded for requests and responses."""

    ALLOW = "allow"
    MODIFY = "modify"
    BLOCK = "block"
    QUARANTINE = "quarantine"


class Severity(str, Enum):
    """Impact levels used for security findings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, Enum):
    """Review lifecycle for a persisted security finding."""

    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"
