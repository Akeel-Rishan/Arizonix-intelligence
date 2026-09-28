from enum import StrEnum

from arizonix_api.db.models.memberships import WorkspaceRole


class WorkspaceAction(StrEnum):
    RENAME = "rename"
    ADD_MEMBER = "add_member"
    CHANGE_ROLE = "change_role"
    REMOVE_MEMBER = "remove_member"


def can_rename(role: WorkspaceRole) -> bool:
    return role in {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}


def can_add_member(actor: WorkspaceRole, new_role: WorkspaceRole) -> bool:
    if actor is WorkspaceRole.OWNER:
        return True
    return actor is WorkspaceRole.ADMIN and new_role in {
        WorkspaceRole.ANALYST,
        WorkspaceRole.VIEWER,
    }


def can_change_role(actor: WorkspaceRole, target: WorkspaceRole, new_role: WorkspaceRole) -> bool:
    if actor is WorkspaceRole.OWNER:
        return True
    mutable = {WorkspaceRole.ANALYST, WorkspaceRole.VIEWER}
    return actor is WorkspaceRole.ADMIN and target in mutable and new_role in mutable


def can_remove_member(actor: WorkspaceRole, target: WorkspaceRole) -> bool:
    if actor is WorkspaceRole.OWNER:
        return True
    return actor is WorkspaceRole.ADMIN and target in {
        WorkspaceRole.ANALYST,
        WorkspaceRole.VIEWER,
    }
