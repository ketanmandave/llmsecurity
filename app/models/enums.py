"""Controlled values persisted by the RAG database."""

from enum import Enum


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Persist string enum values rather than uppercase Python member names."""

    return [str(member.value) for member in enum_class]


class AccessRole(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class Classification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    FAILED = "failed"
    INACTIVE = "inactive"


class SecurityStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    MODIFY = "modify"
    BLOCK = "block"
    QUARANTINE = "quarantine"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"
