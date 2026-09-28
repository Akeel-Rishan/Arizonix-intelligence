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


def translate_database_error(error: DBAPIError) -> Never:
    state = getattr(error.orig, "sqlstate", None)
    mapped = {
        "AR001": DuplicateMembership,
        "AR002": LastOwnerConflict,
        "AR003": PermissionDenied,
        "AR004": WorkspaceNotFound,
        "AR005": ApplicationUserNotFound,
        "AR006": MembershipNotFound,
    }.get(state)
    if mapped is None:
        raise error
    raise mapped from error
