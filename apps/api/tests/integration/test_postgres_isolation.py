import asyncio
import os
from collections.abc import Awaitable, Callable
from contextlib import suppress
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
        reason="set both ARIZONIX_TEST_*_DATABASE_URL values to run real RLS tests",
    ),
]


async def reset_database(admin: AsyncEngine) -> None:
    async with admin.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE arizonix.memberships, arizonix.workspaces, "
                "arizonix.application_users CASCADE"
            )
        )


async def as_user(
    engine: AsyncEngine,
    user_id: UUID,
    operation: Callable[[AsyncConnection], Awaitable[object]],
) -> object:
    async with engine.begin() as connection:
        await connection.execute(
            text("SELECT set_config('arizonix.user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )
        await connection.execute(
            text("SELECT set_config('arizonix.request_id', :request_id, true)"),
            {"request_id": str(uuid4())},
        )
        await connection.execute(
            text("SELECT arizonix.provision_application_user(:user_id, :email)"),
            {"user_id": user_id, "email": f"{user_id}@example.test"},
        )
        return await operation(connection)


async def scalar(connection: AsyncConnection, statement: str, **parameters: object) -> object:
    return await connection.scalar(text(statement), parameters)


def error_state(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def test_real_postgres_rls_roles_and_permission_boundaries() -> None:
    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        runtime = create_async_engine(RUNTIME_URL, pool_size=2, max_overflow=2)
        admin_engine = create_async_engine(MIGRATION_URL)
        await reset_database(admin_engine)
        owner, admin, analyst, viewer, outsider = (uuid4() for _ in range(5))
        try:
            async with admin_engine.connect() as connection:
                assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                    "20261003_0003"
                )

            for user_id in (owner, admin, analyst, viewer, outsider):
                await as_user(runtime, user_id, lambda connection: scalar(connection, "SELECT 1"))

            workspace_id = await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection, "SELECT arizonix.create_workspace(:name)", name="Alpha"
                ),
            )
            assert isinstance(workspace_id, UUID)

            async def add(connection: AsyncConnection, user_id: UUID, role: str) -> object:
                return await scalar(
                    connection,
                    "SELECT arizonix.add_workspace_member(:workspace, :user_id, :role)",
                    workspace=workspace_id,
                    user_id=user_id,
                    role=role,
                )

            await as_user(runtime, owner, lambda connection: add(connection, admin, "admin"))
            await as_user(runtime, owner, lambda connection: add(connection, analyst, "analyst"))
            await as_user(runtime, owner, lambda connection: add(connection, viewer, "viewer"))

            second_workspace = await as_user(
                runtime,
                admin,
                lambda connection: scalar(connection, "SELECT arizonix.create_workspace('Beta')"),
            )
            owner_count = await as_user(
                runtime,
                owner,
                lambda connection: scalar(connection, "SELECT count(*) FROM arizonix.workspaces"),
            )
            admin_count = await as_user(
                runtime,
                admin,
                lambda connection: scalar(connection, "SELECT count(*) FROM arizonix.workspaces"),
            )
            assert owner_count == 1
            assert admin_count == 2

            unrelated_visible = await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT count(*) FROM arizonix.application_users WHERE id = :outsider",
                    outsider=outsider,
                ),
            )
            assert unrelated_visible == 0

            with pytest.raises(DBAPIError) as inaccessible:
                await as_user(
                    runtime,
                    owner,
                    lambda connection: scalar(
                        connection,
                        "SELECT arizonix.rename_workspace(:workspace, 'forged')",
                        workspace=second_workspace,
                    ),
                )
            assert error_state(inaccessible.value) == "AR004"

            await as_user(
                runtime,
                admin,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.rename_workspace(:workspace, 'Renamed by admin')",
                    workspace=workspace_id,
                ),
            )
            await as_user(runtime, admin, lambda connection: add(connection, outsider, "analyst"))
            with pytest.raises(DBAPIError) as duplicate:
                await as_user(
                    runtime, admin, lambda connection: add(connection, outsider, "viewer")
                )
            assert error_state(duplicate.value) == "AR001"

            for actor in (analyst, viewer):
                with pytest.raises(DBAPIError) as denied:
                    await as_user(
                        runtime,
                        actor,
                        lambda connection: scalar(
                            connection,
                            "SELECT arizonix.rename_workspace(:workspace, 'Denied')",
                            workspace=workspace_id,
                        ),
                    )
                assert error_state(denied.value) == "AR003"

            with pytest.raises(DBAPIError) as protected_owner:
                await as_user(
                    runtime,
                    admin,
                    lambda connection: scalar(
                        connection,
                        "SELECT arizonix.change_workspace_member_role"
                        "(:workspace, :owner, 'viewer')",
                        workspace=workspace_id,
                        owner=owner,
                    ),
                )
            assert error_state(protected_owner.value) == "AR003"

            await as_user(
                runtime,
                admin,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.remove_workspace_member(:workspace, :viewer)",
                    workspace=workspace_id,
                    viewer=viewer,
                ),
            )
            viewer_access = await as_user(
                runtime,
                viewer,
                lambda connection: scalar(
                    connection,
                    "SELECT count(*) FROM arizonix.workspaces WHERE id = :workspace",
                    workspace=workspace_id,
                ),
            )
            assert viewer_access == 0

            async with runtime.connect() as connection:
                role = (
                    await connection.execute(
                        text(
                            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
                            "FROM pg_roles WHERE rolname = current_user"
                        )
                    )
                ).one()
                assert tuple(role) == (False, False, False, False)
                owner_name = await connection.scalar(
                    text(
                        "SELECT pg_get_userbyid(relowner) FROM pg_class "
                        "WHERE oid = 'arizonix.workspaces'::regclass"
                    )
                )
                assert owner_name == "arizonix_owner"

            with pytest.raises(DBAPIError):
                await as_user(
                    runtime,
                    owner,
                    lambda connection: scalar(
                        connection,
                        "INSERT INTO arizonix.workspaces(name, created_by) "
                        "VALUES ('Bypass', :owner) RETURNING id",
                        owner=owner,
                    ),
                )
        finally:
            await runtime.dispose()
            await admin_engine.dispose()

    asyncio.run(scenario())


def test_last_owner_concurrency_missing_identity_and_pool_cleanup() -> None:
    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        runtime = create_async_engine(RUNTIME_URL, pool_size=1, max_overflow=1)
        admin_engine = create_async_engine(MIGRATION_URL)
        await reset_database(admin_engine)
        first, second = uuid4(), uuid4()
        try:
            for user_id in (first, second):
                await as_user(runtime, user_id, lambda connection: scalar(connection, "SELECT 1"))
            workspace_id = await as_user(
                runtime,
                first,
                lambda connection: scalar(
                    connection, "SELECT arizonix.create_workspace('Concurrency')"
                ),
            )
            await as_user(
                runtime,
                first,
                lambda connection: scalar(
                    connection,
                    "SELECT arizonix.add_workspace_member(:workspace, :second, 'owner')",
                    workspace=workspace_id,
                    second=second,
                ),
            )

            async def remove(actor: UUID, target: UUID) -> str:
                try:
                    await as_user(
                        runtime,
                        actor,
                        lambda connection: scalar(
                            connection,
                            "SELECT arizonix.remove_workspace_member(:workspace, :target)",
                            workspace=workspace_id,
                            target=target,
                        ),
                    )
                    return "ok"
                except DBAPIError as error:
                    return error_state(error) or "database_error"

            outcomes = await asyncio.gather(remove(first, second), remove(second, first))
            assert outcomes.count("ok") == 1
            assert any(outcome in {"AR002", "AR004"} for outcome in outcomes)

            async with admin_engine.connect() as connection:
                remaining = await connection.scalar(
                    text(
                        "SELECT count(*) FROM arizonix.memberships "
                        "WHERE workspace_id = :workspace AND role = 'owner'"
                    ),
                    {"workspace": workspace_id},
                )
                assert remaining == 1

            remaining_owner = first if outcomes[0] == "ok" else second
            removed_owner = second if outcomes[0] == "ok" else first
            removal_details = await as_user(
                runtime,
                remaining_owner,
                lambda connection: scalar(
                    connection,
                    "SELECT details FROM arizonix.audit_events "
                    "WHERE workspace_id = :workspace AND action = 'membership.removed' "
                    "ORDER BY occurred_at DESC, id DESC LIMIT 1",
                    workspace=workspace_id,
                ),
            )
            assert removal_details["target_user_id"] == str(removed_owner)
            assert removal_details["previous_role"] == "owner"
            with pytest.raises(DBAPIError) as last_owner:
                await as_user(
                    runtime,
                    remaining_owner,
                    lambda connection: scalar(
                        connection,
                        "SELECT arizonix.leave_workspace(:workspace)",
                        workspace=workspace_id,
                    ),
                )
            assert error_state(last_owner.value) == "AR002"

            with pytest.raises(DBAPIError) as missing_identity:
                async with runtime.begin() as connection:
                    identity = await connection.scalar(text("SELECT arizonix.current_user_id()"))
                    visible = await connection.scalar(
                        text("SELECT count(*) FROM arizonix.workspaces")
                    )
                    assert identity is None
                    assert visible == 0
                    await connection.execute(text("SELECT arizonix.create_workspace('Missing')"))
            assert error_state(missing_identity.value) == "AR003"

            with suppress(RuntimeError):
                await as_user(
                    runtime,
                    remaining_owner,
                    lambda connection: (_ for _ in ()).throw(RuntimeError("request failed")),
                )
                async with runtime.begin() as connection:
                    identity = await connection.scalar(text("SELECT arizonix.current_user_id()"))
                    request_id = await connection.scalar(
                        text("SELECT arizonix.current_request_id()")
                    )
                    visible = await connection.scalar(
                        text("SELECT count(*) FROM arizonix.workspaces")
                    )
                    assert identity is None
                    assert request_id is None
                    assert visible == 0
        finally:
            await runtime.dispose()
            await admin_engine.dispose()

    asyncio.run(scenario())


def test_workspace_http_contract_uses_only_the_verified_actor() -> None:
    class TokenVerifier:
        async def verify(self, token: str) -> Principal:
            return Principal(user_id=UUID(token), email=f"{token}@example.test")

    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        admin_engine = create_async_engine(MIGRATION_URL)
        await reset_database(admin_engine)
        owner, viewer, outsider = uuid4(), uuid4(), uuid4()
        settings = Settings(
            _env_file=None,
            app_environment="test",
            allowed_origins=["http://frontend.test"],
            database_url=RUNTIME_URL,
        )
        app = create_app(settings, token_verifier=TokenVerifier())
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://api.test") as client:

                def headers(user_id: UUID) -> dict[str, str]:
                    return {"Authorization": f"Bearer {user_id}"}

                assert (await client.get("/api/v1/workspaces")).status_code == 401
                created = await client.post(
                    "/api/v1/workspaces", headers=headers(owner), json={"name": "HTTP Workspace"}
                )
                assert created.status_code == 201
                workspace_id = created.json()["id"]

                viewer_list = await client.get("/api/v1/workspaces", headers=headers(viewer))
                assert viewer_list.status_code == 200
                assert viewer_list.json()["items"] == []

                forged = await client.post(
                    f"/api/v1/workspaces/{workspace_id}/members",
                    headers=headers(owner),
                    json={
                        "user_id": str(viewer),
                        "role": "viewer",
                        "actor_id": str(outsider),
                    },
                )
                assert forged.status_code == 422

                added = await client.post(
                    f"/api/v1/workspaces/{workspace_id}/members",
                    headers=headers(owner),
                    json={"user_id": str(viewer), "role": "viewer"},
                )
                assert added.status_code == 204

                owner_list = await client.get("/api/v1/workspaces", headers=headers(owner))
                assert [item["id"] for item in owner_list.json()["items"]] == [workspace_id]

                members = await client.get(
                    f"/api/v1/workspaces/{workspace_id}/members", headers=headers(viewer)
                )
                assert members.status_code == 200
                assert {item["user_id"] for item in members.json()["items"]} == {
                    str(owner),
                    str(viewer),
                }

                denied = await client.patch(
                    f"/api/v1/workspaces/{workspace_id}",
                    headers=headers(viewer),
                    json={"name": "Not allowed"},
                )
                assert denied.status_code == 403

                inaccessible = await client.get(
                    f"/api/v1/workspaces/{workspace_id}", headers=headers(outsider)
                )
                assert inaccessible.status_code == 404
        finally:
            await app.state.database.dispose()
            await admin_engine.dispose()

    asyncio.run(scenario())
