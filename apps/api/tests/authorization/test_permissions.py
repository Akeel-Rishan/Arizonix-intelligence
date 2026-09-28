import pytest

from arizonix_api.authorization.permissions import (
    can_add_member,
    can_change_role,
    can_remove_member,
    can_rename,
)
from arizonix_api.db.models.memberships import WorkspaceRole


@pytest.mark.parametrize(
    ("role", "allowed"),
    [("owner", True), ("admin", True), ("analyst", False), ("viewer", False)],
)
def test_rename_permission_matrix(role: str, allowed: bool) -> None:
    assert can_rename(WorkspaceRole(role)) is allowed


@pytest.mark.parametrize("new_role", list(WorkspaceRole))
def test_owner_can_add_and_change_every_role(new_role: WorkspaceRole) -> None:
    assert can_add_member(WorkspaceRole.OWNER, new_role)
    for target in WorkspaceRole:
        assert can_change_role(WorkspaceRole.OWNER, target, new_role)
        assert can_remove_member(WorkspaceRole.OWNER, target)


@pytest.mark.parametrize("role", [WorkspaceRole.ANALYST, WorkspaceRole.VIEWER])
def test_admin_can_manage_only_analysts_and_viewers(role: WorkspaceRole) -> None:
    assert can_add_member(WorkspaceRole.ADMIN, role)
    assert can_change_role(WorkspaceRole.ADMIN, role, WorkspaceRole.ANALYST)
    assert can_change_role(WorkspaceRole.ADMIN, role, WorkspaceRole.VIEWER)
    assert can_remove_member(WorkspaceRole.ADMIN, role)


@pytest.mark.parametrize("protected", [WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
def test_admin_cannot_manage_owner_or_admin(protected: WorkspaceRole) -> None:
    assert not can_add_member(WorkspaceRole.ADMIN, protected)
    assert not can_change_role(WorkspaceRole.ADMIN, protected, WorkspaceRole.VIEWER)
    assert not can_remove_member(WorkspaceRole.ADMIN, protected)


@pytest.mark.parametrize("actor", [WorkspaceRole.ANALYST, WorkspaceRole.VIEWER])
def test_read_only_roles_cannot_administer(actor: WorkspaceRole) -> None:
    for role in WorkspaceRole:
        assert not can_add_member(actor, role)
        assert not can_change_role(actor, role, WorkspaceRole.VIEWER)
        assert not can_remove_member(actor, role)
