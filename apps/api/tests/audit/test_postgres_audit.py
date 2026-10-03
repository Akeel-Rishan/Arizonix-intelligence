import asyncio
import os
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from arizonix_api.auth.principal import Principal
from arizonix_api.config import Settings
from arizonix_api.main import create_app

RUNTIME_URL = os.getenv("ARIZONIX_TEST_RUNTIME_DATABASE_URL")
MIGRATION_URL = os.getenv("ARIZONIX_TEST_MIGRATION_DATABASE_URL")
pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not RUNTIME_URL or not MIGRATION_URL,
        reason="set both ARIZONIX_TEST_*_DATABASE_URL values to run real audit tests",
    ),
]


async def reset_database(admin: AsyncEngine) -> None:
    async with admin.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE arizonix.audit_events, arizonix.memberships, "
                "arizonix.workspaces, arizonix.application_users CASCADE"
            )
        )


async def as_user(
    engine: AsyncEngine,
    user_id: UUID,
    operation: Callable[[AsyncConnection], Awaitable[object]],
    *,
    request_id: UUID | None = None,
) -> object:
    async with engine.begin() as connection:
        await connection.execute(
            text("SELECT set_config('arizonix.user_id', :value, true)"), {"value": str(user_id)}
        )
        await connection.execute(
            text("SELECT set_config('arizonix.request_id', :value, true)"),
            {"value": str(request_id or uuid4())},
        )
        await connection.execute(
            text("SELECT arizonix.provision_application_user(:id, :email)"),
            {"id": user_id, "email": f"{user_id}@example.test"},
        )
        return await operation(connection)


async def scalar(connection: AsyncConnection, sql: str, **params: object) -> object:
    return await connection.scalar(text(sql), params)


def sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def test_audit_events_are_atomic_complete_and_runtime_append_only() -> None:
    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        runtime = create_async_engine(RUNTIME_URL, pool_size=2, max_overflow=2)
        admin = create_async_engine(MIGRATION_URL)
        owner, admin_user, analyst, rollback_user = (uuid4() for _ in range(4))
        correlation = uuid4()
        await reset_database(admin)
        try:
            async with runtime.connect() as connection:
                transaction = await connection.begin()
                await connection.execute(
                    text("SELECT set_config('arizonix.user_id', :value, true)"),
                    {"value": str(rollback_user)},
                )
                await connection.execute(
                    text("SELECT set_config('arizonix.request_id', :value, true)"),
                    {"value": str(uuid4())},
                )
                await connection.execute(
                    text("SELECT arizonix.provision_application_user(:id, null)"),
                    {"id": rollback_user},
                )
                await connection.execute(text("SELECT arizonix.create_workspace('Rolled Back')"))
                await transaction.rollback()
            async with admin.connect() as connection:
                assert (
                    await connection.scalar(
                        text("SELECT count(*) FROM arizonix.workspaces WHERE name = 'Rolled Back'")
                    )
                    == 0
                )
                assert (
                    await connection.scalar(text("SELECT count(*) FROM arizonix.audit_events")) == 0
                )

            for user_id in (owner, admin_user, analyst):
                await as_user(runtime, user_id, lambda connection: scalar(connection, "SELECT 1"))
            workspace_id = await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection, "SELECT arizonix.create_workspace('Northstar')"
                ),
                request_id=correlation,
            )
            assert isinstance(workspace_id, UUID)
            await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.add_workspace_member(:workspace, :user_id, 'admin')",
                    workspace=workspace_id,
                    user_id=admin_user,
                ),
            )
            await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.add_workspace_member(:workspace, :user_id, 'analyst')",
                    workspace=workspace_id,
                    user_id=analyst,
                ),
            )
            await as_user(
                runtime,
                admin_user,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.rename_workspace(:workspace, 'Signal Lab')",
                    workspace=workspace_id,
                ),
            )
            await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.change_workspace_member_role(:workspace, :user_id, 'viewer')",
                    workspace=workspace_id,
                    user_id=analyst,
                ),
            )

            async def read_events(connection: AsyncConnection) -> list[tuple[object, ...]]:
                result = await connection.execute(
                    text(
                        "SELECT action::text, actor_user_id, target_id, request_id, details "
                        "FROM arizonix.audit_events WHERE workspace_id = :workspace "
                        "ORDER BY occurred_at, id"
                    ),
                    {"workspace": workspace_id},
                )
                return [tuple(row) for row in result]

            events = await as_user(runtime, owner, read_events)
            assert [event[0] for event in events] == [
                "workspace.created",
                "membership.added",
                "membership.added",
                "workspace.renamed",
                "membership.role_changed",
            ]
            assert events[0][1:4] == (owner, workspace_id, correlation)
            assert events[3][4] == {"new_name": "Signal Lab", "previous_name": "Northstar"}
            assert events[4][4]["previous_role"] == "analyst"
            assert events[4][4]["new_role"] == "viewer"

            count_before = len(events)
            await as_user(
                runtime,
                admin_user,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.rename_workspace(:workspace, 'Signal Lab')",
                    workspace=workspace_id,
                ),
            )
            assert len(await as_user(runtime, owner, read_events)) == count_before

            analyst_visible = await as_user(
                runtime,
                analyst,
                lambda connection: scalar(
                    connection,
                    "SELECT count(*) FROM arizonix.audit_events WHERE workspace_id = :workspace",
                    workspace=workspace_id,
                ),
            )
            assert analyst_visible == 0

            for statement in (
                "UPDATE arizonix.audit_events SET details = '{}'::jsonb",
                "DELETE FROM arizonix.audit_events",
                "TRUNCATE arizonix.audit_events",
                "INSERT INTO arizonix.audit_events "
                "(workspace_id, actor_user_id, action, target_type, target_id, request_id) "
                "VALUES (:workspace, :owner, 'workspace.created', 'workspace', "
                ":workspace, :request)",
                "ALTER TABLE arizonix.audit_events DISABLE TRIGGER ALL",
                "ALTER FUNCTION arizonix.write_audit_event"
                "(uuid, arizonix.audit_action, text, uuid, jsonb) OWNER TO arizonix_runtime",
            ):
                with pytest.raises(DBAPIError):
                    await as_user(
                        runtime,
                        owner,
                        lambda connection, query=statement: connection.execute(
                            text(query),
                            {"workspace": workspace_id, "owner": owner, "request": uuid4()},
                        ),
                    )

            async with runtime.connect() as connection:
                may_write = await connection.scalar(
                    text(
                        "SELECT has_function_privilege(current_user, "
                        "'arizonix.write_audit_event(uuid, arizonix.audit_action, text, uuid, "
                        "jsonb)', "
                        "'EXECUTE')"
                    )
                )
                assert may_write is False

            async with admin.begin() as connection:
                await connection.execute(
                    text(
                        "ALTER TABLE arizonix.audit_events ADD CONSTRAINT audit_forced_failure "
                        "CHECK (false) NOT VALID"
                    )
                )
            try:
                with pytest.raises(DBAPIError) as failed_audit:
                    await as_user(
                        runtime,
                        admin_user,
                        lambda connection: scalar(
                            connection,
                            "SELECT arizonix.rename_workspace(:workspace, 'Must Roll Back')",
                            workspace=workspace_id,
                        ),
                    )
                assert sqlstate(failed_audit.value) == "AR007"
            finally:
                async with admin.begin() as connection:
                    await connection.execute(
                        text(
                            "ALTER TABLE arizonix.audit_events DROP CONSTRAINT audit_forced_failure"
                        )
                    )
            current_name = await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT name FROM arizonix.workspaces WHERE id = :workspace",
                    workspace=workspace_id,
                ),
            )
            assert current_name == "Signal Lab"

            await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.remove_workspace_member(:workspace, :user_id)",
                    workspace=workspace_id,
                    user_id=admin_user,
                ),
            )

            await as_user(
                runtime,
                analyst,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.leave_workspace(:workspace)",
                    workspace=workspace_id,
                ),
            )
            final_events = await as_user(runtime, owner, read_events)
            assert [event[0] for event in final_events[-2:]] == [
                "membership.removed",
                "membership.left",
            ]
            assert final_events[-2][2] == admin_user
            assert final_events[-2][4]["previous_role"] == "admin"
            assert final_events[-1][2] == analyst
            assert final_events[-1][4]["previous_role"] == "viewer"
        finally:
            await runtime.dispose()
            await admin.dispose()

    asyncio.run(scenario())


def test_audit_http_authorization_filters_pagination_and_cross_workspace_ids() -> None:
    class TokenVerifier:
        async def verify(self, token: str) -> Principal:
            return Principal(user_id=UUID(token), email=f"{token}@example.test")

    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        admin_engine = create_async_engine(MIGRATION_URL)
        await reset_database(admin_engine)
        owner, admin_user, viewer, outsider = uuid4(), uuid4(), uuid4(), uuid4()
        app = create_app(
            Settings(
                _env_file=None,
                app_environment="test",
                allowed_origins=["http://frontend.test"],
                database_url=RUNTIME_URL,
            ),
            token_verifier=TokenVerifier(),
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://api.test"
            ) as client:
                headers = lambda user: {"Authorization": f"Bearer {user}"}  # noqa: E731
                created = await client.post(
                    "/api/v1/workspaces", headers=headers(owner), json={"name": "Audit API"}
                )
                workspace_id = created.json()["id"]
                for user, role in ((admin_user, "admin"), (viewer, "viewer")):
                    await client.get("/api/v1/workspaces", headers=headers(user))
                    assert (
                        await client.post(
                            f"/api/v1/workspaces/{workspace_id}/members",
                            headers=headers(owner),
                            json={"user_id": str(user), "role": role},
                        )
                    ).status_code == 204

                owner_page = await client.get(
                    f"/api/v1/workspaces/{workspace_id}/audit-events?limit=1",
                    headers=headers(owner),
                )
                assert owner_page.status_code == 200
                assert owner_page.headers["cache-control"] == "private, no-store"
                first = owner_page.json()
                assert len(first["items"]) == 1 and first["next_cursor"]
                second = await client.get(
                    f"/api/v1/workspaces/{workspace_id}/audit-events",
                    headers=headers(owner),
                    params={"limit": 1, "cursor": first["next_cursor"]},
                )
                assert second.status_code == 200
                assert second.json()["items"][0]["id"] != first["items"][0]["id"]
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events",
                        headers=headers(admin_user),
                        params={"action": "membership.added"},
                    )
                ).status_code == 200
                assert (
                    await client.patch(
                        f"/api/v1/workspaces/{workspace_id}/members/{admin_user}",
                        headers=headers(owner),
                        json={"role": "viewer"},
                    )
                ).status_code == 204
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events",
                        headers=headers(admin_user),
                    )
                ).status_code == 403
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events",
                        headers=headers(viewer),
                    )
                ).status_code == 403
                assert (
                    await client.delete(
                        f"/api/v1/workspaces/{workspace_id}/members/{viewer}",
                        headers=headers(owner),
                    )
                ).status_code == 204
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events",
                        headers=headers(viewer),
                    )
                ).status_code == 404
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events",
                        headers=headers(outsider),
                    )
                ).status_code == 404
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events?cursor=not-valid",
                        headers=headers(owner),
                    )
                ).status_code == 400

                other = await client.post(
                    "/api/v1/workspaces", headers=headers(outsider), json={"name": "Other"}
                )
                other_event = (
                    await client.get(
                        f"/api/v1/workspaces/{other.json()['id']}/audit-events",
                        headers=headers(outsider),
                    )
                ).json()["items"][0]["id"]
                assert (
                    await client.get(
                        f"/api/v1/workspaces/{workspace_id}/audit-events/{other_event}",
                        headers=headers(owner),
                    )
                ).status_code == 404
        finally:
            await app.state.database.dispose()
            await admin_engine.dispose()

    asyncio.run(scenario())
