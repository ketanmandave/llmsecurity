from app.gateway.authorization.decision import AuthorizationStatus

GENERAL_ASSISTANT = "general_assistant"
PAYROLL = "payroll"
SALARY = "salary"
HR_RECORDS = "hr_records"
SECURITY_ANALYTICS = "security_analytics"
SECURITY_POLICY = "security_policy"

RESOURCE_ACTIONS = {
    GENERAL_ASSISTANT: "read",
    PAYROLL: "read",
    SALARY: "read",
    HR_RECORDS: "read",
    SECURITY_ANALYTICS: "view",
    SECURITY_POLICY: "change",
}

RESOURCE_PATTERNS = {
    PAYROLL: ("payroll",),
    SALARY: ("employee salaries", "employee salary", "salary"),
    HR_RECORDS: ("hr records", "human resources records"),
    SECURITY_ANALYTICS: ("sentinelai attacks", "sentinelai attack"),
    SECURITY_POLICY: ("change security policy",),
}

ROLE_POLICIES = {
    "employee": {GENERAL_ASSISTANT: AuthorizationStatus.ALLOW},
    "manager": {GENERAL_ASSISTANT: AuthorizationStatus.ALLOW, PAYROLL: AuthorizationStatus.REVIEW, SALARY: AuthorizationStatus.REVIEW},
    "hr": {GENERAL_ASSISTANT: AuthorizationStatus.ALLOW, HR_RECORDS: AuthorizationStatus.ALLOW},
    "payroll administrator": {GENERAL_ASSISTANT: AuthorizationStatus.ALLOW, PAYROLL: AuthorizationStatus.ALLOW, SALARY: AuthorizationStatus.ALLOW},
    "security analyst": {GENERAL_ASSISTANT: AuthorizationStatus.ALLOW, SECURITY_ANALYTICS: AuthorizationStatus.ALLOW},
    "sentinelai administrator": {GENERAL_ASSISTANT: AuthorizationStatus.ALLOW, SECURITY_ANALYTICS: AuthorizationStatus.ALLOW, SECURITY_POLICY: AuthorizationStatus.ALLOW},
}
