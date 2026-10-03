from typing import Never

from sqlalchemy.exc import DBAPIError


class WorkspaceServiceError(Exception):
    code = "workspace_error"


class WorkspaceNotFound(WorkspaceServiceError):
    code = "workspace_not_found"


class PermissionDenied(WorkspaceServiceError):
    code = "permission_denied"


class ApplicationUserNotFound(WorkspaceServiceError):
    code = "application_user_not_found"


class DuplicateMembership(WorkspaceServiceError):
    code = "duplicate_membership"


class LastOwnerConflict(WorkspaceServiceError):
    code = "last_owner"


class MembershipNotFound(WorkspaceServiceError):
    code = "membership_not_found"


class AuditEventNotFound(WorkspaceServiceError):
    code = "audit_event_not_found"


class InvalidAuditQuery(WorkspaceServiceError):
    code = "invalid_audit_query"


class AuditPersistenceFailure(WorkspaceServiceError):
    code = "audit_persistence_failed"


class CompanyNotFound(WorkspaceServiceError):
    code = "company_not_found"


class VersionConflict(WorkspaceServiceError):
    code = "version_conflict"


class CompanyLifecycleConflict(WorkspaceServiceError):
    code = "company_lifecycle_conflict"


class InvalidCompanyQuery(WorkspaceServiceError):
    code = "invalid_company_query"


def translate_database_error(error: DBAPIError) -> Never:
    state = getattr(error.orig, "sqlstate", None)
    mapped = {
        "AR001": DuplicateMembership,
        "AR002": LastOwnerConflict,
        "AR003": PermissionDenied,
        "AR004": WorkspaceNotFound,
        "AR005": ApplicationUserNotFound,
        "AR006": MembershipNotFound,
        "AR007": AuditPersistenceFailure,
        "AR008": VersionConflict,
        "AR009": CompanyLifecycleConflict,
        "AR010": CompanyNotFound,
    }.get(state)
    if mapped is None:
        raise error
    raise mapped from error
