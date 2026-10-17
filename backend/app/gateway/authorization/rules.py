import re
from dataclasses import dataclass

from app.gateway.authorization.config import GENERAL_ASSISTANT, RESOURCE_ACTIONS, RESOURCE_PATTERNS, ROLE_POLICIES
from app.gateway.authorization.decision import AuthorizationStatus
from app.gateway.context import RequestContext


@dataclass(frozen=True)
class RuleMatch:
    resource: str
    action: str
    status: AuthorizationStatus
    matched_rule: str


class AuthorizationRule:
    def evaluate(self, context: RequestContext) -> RuleMatch:
        prompt = re.sub(r"\s+", " ", context.prompt.casefold()).strip()
        resource = next(
            (name for name, patterns in RESOURCE_PATTERNS.items() if any(pattern in prompt for pattern in patterns)),
            GENERAL_ASSISTANT,
        )
        status = ROLE_POLICIES.get(context.role.casefold(), {}).get(resource, AuthorizationStatus.DENY)
        return RuleMatch(resource, RESOURCE_ACTIONS[resource], status, "RoleResourcePolicy")
