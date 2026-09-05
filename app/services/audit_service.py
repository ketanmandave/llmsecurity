"""Privacy-conscious security audit persistence."""

import hashlib
import uuid

from app.auth.jwt import Principal
from app.database import AsyncSessionFactory
from app.models import AuditEvent, PolicyDecision


def text_sha256(text: str) -> str:
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
                    user_roles=sorted(role.value for role in principal.roles),
                    action=action,
                    decision=decision,
                    document_ids=list(dict.fromkeys(document_ids)),
                    details=details,
                )
            )
