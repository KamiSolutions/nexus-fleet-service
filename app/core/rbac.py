"""
Role/permission model — Python mirror of the frontend's source of truth.

This file must stay in lockstep with lib/permissions.ts in the nexus-portal
Expo app. That file is the canonical definition (it's what actually drives
the sidebar and PermissionsProvider today); this module mirrors it so the
backend can embed the same permission strings in a JWT's `scopes` claim
and enforce them via FastAPI SecurityScopes.

If you change a role or a module in either file, change both in the same
commit. There is no code generation wiring these together yet (P1 item:
generate one from the other, e.g. a shared JSON schema) — until then, this
comment is the enforcement mechanism.

DRIVER and MORTUARY_STAFF exist because every role before them was
back-office (finance/HR/fleet/claims/admin) with no representation of the
field-operations side (vehicle dispatch, case intake, mortuary logistics)
the platform is actually built around.
"""

from __future__ import annotations

from enum import Enum


class EnterpriseRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    GROUP_ADMIN = "GROUP_ADMIN"
    COMPANY_ADMIN = "COMPANY_ADMIN"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    HR_MANAGER = "HR_MANAGER"
    FLEET_MANAGER = "FLEET_MANAGER"
    CLAIMS_OFFICER = "CLAIMS_OFFICER"
    MORTUARY_STAFF = "MORTUARY_STAFF"
    DRIVER = "DRIVER"
    TEAM_LEAD = "TEAM_LEAD"
    EMPLOYEE = "EMPLOYEE"
    AUDITOR = "AUDITOR"


PermissionAction = str  # "view" | "create" | "approve" | "manage" | "export"
PermissionModule = str

ALL_MODULES: tuple[str, ...] = (
    "dashboard",
    "companies",
    "employees",
    "finance",
    "hr",
    "vehicles",
    "cases",
    "leases",
    "policies",
    "claims",
    "analytics",
    "reports",
    "billing",
    "settings",
    "admin",
)

ALL_ACTIONS: tuple[str, ...] = ("view", "create", "approve", "manage", "export")

_FULL_ACCESS: list[str] = [f"{module}:{action}" for module in ALL_MODULES for action in ALL_ACTIONS]

ROLE_LABELS: dict[EnterpriseRole, str] = {
    EnterpriseRole.SUPER_ADMIN: "Super Admin",
    EnterpriseRole.GROUP_ADMIN: "Group Admin",
    EnterpriseRole.COMPANY_ADMIN: "Company Admin",
    EnterpriseRole.FINANCE_MANAGER: "Finance Manager",
    EnterpriseRole.HR_MANAGER: "HR Manager",
    EnterpriseRole.FLEET_MANAGER: "Fleet Manager",
    EnterpriseRole.CLAIMS_OFFICER: "Claims Officer",
    EnterpriseRole.MORTUARY_STAFF: "Mortuary Staff",
    EnterpriseRole.DRIVER: "Driver",
    EnterpriseRole.TEAM_LEAD: "Team Lead",
    EnterpriseRole.EMPLOYEE: "Employee",
    EnterpriseRole.AUDITOR: "Read-only Auditor",
}

ROLE_PERMISSIONS: dict[EnterpriseRole, list[str]] = {
    EnterpriseRole.SUPER_ADMIN: _FULL_ACCESS,
    EnterpriseRole.GROUP_ADMIN: [p for p in _FULL_ACCESS if not p.startswith("billing:manage")],
    EnterpriseRole.COMPANY_ADMIN: [
        "dashboard:view",
        "companies:view",
        "employees:view",
        "employees:create",
        "employees:manage",
        "finance:view",
        "finance:approve",
        "hr:view",
        "hr:approve",
        "vehicles:view",
        "vehicles:manage",
        "leases:view",
        "policies:view",
        "claims:view",
        "analytics:view",
        "reports:view",
        "settings:view",
    ],
    EnterpriseRole.FINANCE_MANAGER: [
        "dashboard:view",
        "finance:view",
        "finance:create",
        "finance:approve",
        "finance:export",
        "analytics:view",
        "reports:view",
    ],
    EnterpriseRole.HR_MANAGER: [
        "dashboard:view",
        "employees:view",
        "employees:create",
        "hr:view",
        "hr:create",
        "hr:approve",
        "reports:view",
    ],
    EnterpriseRole.FLEET_MANAGER: [
        "dashboard:view",
        "vehicles:view",
        "vehicles:create",
        "vehicles:manage",
        "reports:view",
    ],
    EnterpriseRole.CLAIMS_OFFICER: [
        "dashboard:view",
        "policies:view",
        "claims:view",
        "claims:create",
        "claims:approve",
    ],
    EnterpriseRole.MORTUARY_STAFF: [
        "dashboard:view",
        "cases:view",
        "cases:create",
        "cases:manage",
        "vehicles:view",
    ],
    EnterpriseRole.DRIVER: ["dashboard:view", "vehicles:view"],
    EnterpriseRole.TEAM_LEAD: [
        "dashboard:view",
        "employees:view",
        "hr:view",
        "finance:view",
        "finance:create",
    ],
    EnterpriseRole.EMPLOYEE: ["dashboard:view", "hr:view", "hr:create", "claims:view", "claims:create"],
    EnterpriseRole.AUDITOR: [f"{module}:view" for module in ALL_MODULES],
}


def scopes_for_role(role: EnterpriseRole) -> list[str]:
    """The permission strings to embed in a token's `scopes` claim for `role`."""
    return ROLE_PERMISSIONS[role]


def can(role: EnterpriseRole, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS[role]
