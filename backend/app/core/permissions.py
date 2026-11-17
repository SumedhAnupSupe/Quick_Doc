"""Permission catalogue and the default role -> permission matrix.

Permissions are plain strings ("domain:action"). They are seeded into the `permissions`
and `role_permissions` tables, and enforced by backend dependencies (never UI-only).
"""
from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    AICTE_ADMIN = "aicte_admin"
    STATE_ADMIN = "state_admin"
    INSTITUTION_ADMIN = "institution_admin"
    INSTITUTION_STAFF = "institution_staff"
    VERIFICATION_OFFICER = "verification_officer"


# Roles whose data scope is the whole platform.
PLATFORM_ROLES = {Role.SUPER_ADMIN, Role.AICTE_ADMIN}
INSTITUTION_ROLES = {Role.INSTITUTION_ADMIN, Role.INSTITUTION_STAFF}

PERMISSIONS: dict[str, str] = {
    "user:read": "View users in scope",
    "user:manage": "Create/update users and statuses",
    "role:assign": "Assign roles to users",
    "role:manage": "View/manage role-permission matrix",
    "institution:read": "View institutions in scope",
    "institution:manage": "Create/edit institutions",
    "institution:approve": "Approve/reject/suspend/reactivate institutions",
    "academic:read": "View years, programmes, intakes",
    "academic:manage": "Manage years, programmes, intakes",
    "person:read": "View persons in scope",
    "person:write": "Create/update persons",
    "enrolment:read": "View enrolments in scope",
    "enrolment:write": "Create/update enrolments",
    "enrolment:submit": "Submit enrolments for verification",
    "document_type:read": "View document types",
    "document_type:manage_central": "Manage Central Vault document types",
    "document_type:manage_state": "Manage State Vault document types",
    "document:read": "View/download documents in scope",
    "document:write": "Upload/replace documents",
    "verification:read": "View verification queues",
    "verification:decide": "Approve/reject/request correction",
    "duplicate:read": "View duplicate cases",
    "duplicate:resolve": "Assign/resolve duplicate cases",
    "import:read": "View bulk imports in scope",
    "import:write": "Upload/confirm bulk imports",
    "analytics:read": "View dashboards",
    "report:export": "Export reports",
    "audit:read": "View audit logs",
    "security:read": "View security events",
    "security:manage": "Resolve security events",
    "settings:manage": "Platform settings",
}

_ALL = set(PERMISSIONS)

ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.SUPER_ADMIN: _ALL,
    Role.AICTE_ADMIN: _ALL - {"role:assign", "role:manage", "settings:manage", "document_type:manage_state"},
    Role.STATE_ADMIN: {
        "user:read", "institution:read", "academic:read", "person:read", "enrolment:read",
        "document_type:read", "document_type:manage_state", "document:read",
        "verification:read", "verification:decide", "duplicate:read",
        "analytics:read", "report:export", "import:read",
    },
    Role.INSTITUTION_ADMIN: {
        "user:read", "user:manage", "institution:read", "academic:read",
        "person:read", "person:write", "enrolment:read", "enrolment:write", "enrolment:submit",
        "document_type:read", "document:read", "document:write",
        "import:read", "import:write", "analytics:read", "report:export", "verification:read",
    },
    Role.INSTITUTION_STAFF: {
        "institution:read", "academic:read",
        "person:read", "person:write", "enrolment:read", "enrolment:write", "enrolment:submit",
        "document_type:read", "document:read", "document:write",
        "import:read", "import:write", "analytics:read",
    },
    Role.VERIFICATION_OFFICER: {
        "institution:read", "academic:read", "person:read", "enrolment:read",
        "document_type:read", "document:read",
        "verification:read", "verification:decide",
        "duplicate:read", "duplicate:resolve", "analytics:read",
    },
}
