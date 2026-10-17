"""Privacy-conscious security audit persistence."""

import hashlib
import uuid

from app.rag.auth.jwt import Principal
from app.rag.database import AsyncSessionFactory
from app.rag.models import AuditEvent, PolicyDecision


def text_sha256(text: str) -> str:
    """Hash request text for correlation without storing its raw value."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def write_audit_event(
    request_id: uuid.UUID,
    principal: Principal,
    action: str,
    decision: PolicyDecision,
    document_ids: list[uuid.UUID],
    details: dict,
) -> None:
    """Commit an audit event independently, without raw prompt or response text."""

    async with AsyncSessionFactory() as session:
        async with session.begin():
            session.add(
                AuditEvent(
                    request_id=str(request_id),
                    user_id=principal.user_id,
                    user_roles=[principal.role_slug],
                    action=action,
                    decision=decision,
                    document_ids=list(dict.fromkeys(document_ids)),
                    details=details,
                )
            )
