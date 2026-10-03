import asyncio
import os
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from arizonix_api.auth.principal import Principal
from arizonix_api.config import Settings
from arizonix_api.main import create_app

RUNTIME_URL = os.getenv("ARIZONIX_TEST_RUNTIME_DATABASE_URL")
MIGRATION_URL = os.getenv("ARIZONIX_TEST_MIGRATION_DATABASE_URL")
pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not RUNTIME_URL or not MIGRATION_URL,
        reason="set both ARIZONIX_TEST_*_DATABASE_URL values to run company database tests",
    ),
]


async def as_user(
    connection_factory, user_id: UUID, operation: Callable[[AsyncConnection], Awaitable[object]]
) -> object:
    async with connection_factory.begin() as connection:
        await connection.execute(
            text("SELECT set_config('arizonix.user_id', :value, true)"), {"value": str(user_id)}
        )
        await connection.execute(
            text("SELECT set_config('arizonix.request_id', :value, true)"),
            {"value": str(uuid4())},
        )
        await connection.execute(
            text("SELECT arizonix.provision_application_user(:id, :email)"),
            {"id": user_id, "email": f"{user_id}@example.test"},
        )
        return await operation(connection)


async def scalar(connection: AsyncConnection, statement: str, **parameters: object) -> object:
    return await connection.scalar(text(statement), parameters)


def state(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def test_company_permissions_lifecycle_concurrency_rls_and_audit() -> None:
    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        runtime = create_async_engine(RUNTIME_URL)
        admin_engine = create_async_engine(MIGRATION_URL)
        owner, analyst, viewer, outsider = (uuid4() for _ in range(4))
        try:
            async with admin_engine.begin() as connection:
                await connection.execute(
                    text(
                        "TRUNCATE arizonix.audit_events, arizonix.companies, "
                        "arizonix.memberships, arizonix.workspaces, "
                        "arizonix.application_users CASCADE"
                    )
                )
            for user in (owner, analyst, viewer, outsider):
                await as_user(runtime, user, lambda connection: scalar(connection, "SELECT 1"))
            workspace_id = await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection, "SELECT arizonix.create_workspace('Company test')"
                ),
            )
            assert isinstance(workspace_id, UUID)

            async def add(connection: AsyncConnection, user: UUID, role: str) -> object:
                return await scalar(
                    connection,
                    "SELECT arizonix.add_workspace_member(:workspace, :user, :role)",
                    workspace=workspace_id,
                    user=user,
                    role=role,
                )

            await as_user(runtime, owner, lambda connection: add(connection, analyst, "analyst"))
            await as_user(runtime, owner, lambda connection: add(connection, viewer, "viewer"))

            create_sql = (
                "SELECT arizonix.create_company(:workspace, :name, :url, :industry, "
                ":country, :description, :notes)"
            )

            async def create(connection: AsyncConnection) -> object:
                return await scalar(
                    connection,
                    create_sql,
                    workspace=workspace_id,
                    name="Acme Ω",
                    url="https://example.test",
                    industry="Logistics",
                    country="lk",
                    description="Candidate",
                    notes="secret note",
                )

            company_id = await as_user(runtime, analyst, create)
            assert isinstance(company_id, UUID)

            async def denied_create(connection: AsyncConnection) -> object:
                with pytest.raises(DBAPIError) as denied:
                    async with connection.begin_nested():
                        await create(connection)
                assert state(denied.value) == "AR003"
                return None

            await as_user(runtime, viewer, denied_create)
            viewer_count = await as_user(
                runtime,
                viewer,
                lambda connection: scalar(
                    connection,
                    "SELECT count(*) FROM arizonix.companies WHERE workspace_id = :workspace",
                    workspace=workspace_id,
                ),
            )
            outsider_count = await as_user(
                runtime,
                outsider,
                lambda connection: scalar(connection, "SELECT count(*) FROM arizonix.companies"),
            )
            assert viewer_count == 1
            assert outsider_count == 0

            update_sql = (
                "SELECT arizonix.update_company(:workspace, :company, :version, "
                "false, NULL, false, NULL, true, :industry, false, NULL, false, NULL, "
                "false, NULL)"
            )

            async def update(connection: AsyncConnection) -> object:
                return await scalar(
                    connection,
                    update_sql,
                    workspace=workspace_id,
                    company=company_id,
                    version=1,
                    industry="Supply chain",
                )

            await as_user(runtime, owner, update)

            async def stale_update(connection: AsyncConnection) -> object:
                with pytest.raises(DBAPIError) as stale:
                    async with connection.begin_nested():
                        await update(connection)
                assert state(stale.value) == "AR008"
                return None

            await as_user(runtime, analyst, stale_update)

            async def no_op(connection: AsyncConnection) -> object:
                return await scalar(
                    connection,
                    update_sql,
                    workspace=workspace_id,
                    company=company_id,
                    version=2,
                    industry="Supply chain",
                )

            await as_user(runtime, analyst, no_op)
            audit_before_archive = await as_user(
                runtime,
                owner,
                lambda connection: scalar(
                    connection,
                    "SELECT count(*) FROM arizonix.audit_events WHERE target_id = :company",
                    company=company_id,
                ),
            )
            assert audit_before_archive == 2

            lifecycle_sql = (
                "SELECT arizonix.set_company_archived(:workspace, :company, :version, :archived)"
            )

            async def archive(connection: AsyncConnection) -> object:
                return await scalar(
                    connection,
                    lifecycle_sql,
                    workspace=workspace_id,
                    company=company_id,
                    version=2,
                    archived=True,
                )

            await as_user(runtime, owner, archive)

            async def archived_edit(connection: AsyncConnection) -> object:
                with pytest.raises(DBAPIError) as conflict:
                    async with connection.begin_nested():
                        await scalar(
                            connection,
                            update_sql,
                            workspace=workspace_id,
                            company=company_id,
                            version=3,
                            industry="Other",
                        )
                assert state(conflict.value) == "AR009"
                return None

            await as_user(runtime, analyst, archived_edit)
            await as_user(
                runtime,
                analyst,
                lambda connection: scalar(
                    connection,
                    lifecycle_sql,
                    workspace=workspace_id,
                    company=company_id,
                    version=3,
                    archived=False,
                ),
            )
            final_version = await as_user(
                runtime,
                viewer,
                lambda connection: scalar(
                    connection,
                    "SELECT version FROM arizonix.companies WHERE id = :company",
                    company=company_id,
                ),
            )
            assert final_version == 4

            race_sql = (
                "SELECT arizonix.update_company(:workspace, :company, 4, "
                "true, :name, false, NULL, false, NULL, false, NULL, false, NULL, "
                "false, NULL)"
            )

            async def race(connection: AsyncConnection, name: str) -> object:
                try:
                    async with connection.begin_nested():
                        await scalar(
                            connection,
                            race_sql,
                            workspace=workspace_id,
                            company=company_id,
                            name=name,
                        )
                    return "ok"
                except DBAPIError as error:
                    return state(error)

            race_results = await asyncio.gather(
                as_user(runtime, owner, lambda connection: race(connection, "Concurrent one")),
                as_user(runtime, analyst, lambda connection: race(connection, "Concurrent two")),
            )
            assert sorted(race_results) == ["AR008", "ok"]

            async def forbidden_delete(connection: AsyncConnection) -> object:
                with pytest.raises(DBAPIError):
                    async with connection.begin_nested():
                        await connection.execute(
                            text("DELETE FROM arizonix.companies WHERE id = :company"),
                            {"company": company_id},
                        )
                return None

            await as_user(runtime, owner, forbidden_delete)

            async def demote(connection: AsyncConnection) -> object:
                return await scalar(
                    connection,
                    "SELECT arizonix.change_workspace_member_role(:workspace, :user, 'viewer')",
                    workspace=workspace_id,
                    user=analyst,
                )

            await as_user(runtime, owner, demote)

            async def denied_after_demotion(connection: AsyncConnection) -> object:
                with pytest.raises(DBAPIError) as denied:
                    async with connection.begin_nested():
                        await scalar(
                            connection,
                            race_sql,
                            workspace=workspace_id,
                            company=company_id,
                            name="Forbidden",
                        )
                assert state(denied.value) == "AR003"
                return None

            await as_user(runtime, analyst, denied_after_demotion)

            async with admin_engine.connect() as connection:
                details = await connection.scalar(
                    text(
                        "SELECT details FROM arizonix.audit_events "
                        "WHERE action = 'company.updated' AND target_id = :company"
                    ),
                    {"company": company_id},
                )
                assert details["changed_fields"] == ["industry"]
                assert "secret note" not in str(details)
                assert "example.test" not in str(details)
        finally:
            await runtime.dispose()
            await admin_engine.dispose()

    asyncio.run(scenario())


def test_company_http_validation_filters_pagination_and_partial_updates() -> None:
    class TokenVerifier:
        async def verify(self, token: str) -> Principal:
            return Principal(user_id=UUID(token), email=f"{token}@example.test")

    async def scenario() -> None:
        assert RUNTIME_URL and MIGRATION_URL
        admin_engine = create_async_engine(MIGRATION_URL)
        async with admin_engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE arizonix.audit_events, arizonix.companies, "
                    "arizonix.memberships, arizonix.workspaces, "
                    "arizonix.application_users CASCADE"
                )
            )
        owner, analyst, viewer = uuid4(), uuid4(), uuid4()
        app = create_app(
            Settings(_env_file=None, app_environment="test", database_url=RUNTIME_URL),
            token_verifier=TokenVerifier(),
        )
        transport = ASGITransport(app=app)

        def headers(user: UUID) -> dict[str, str]:
            return {"Authorization": f"Bearer {user}"}

        try:
            async with AsyncClient(transport=transport, base_url="http://api.test") as client:
                workspace_response = await client.post(
                    "/api/v1/workspaces", headers=headers(owner), json={"name": "HTTP companies"}
                )
                workspace = workspace_response.json()["id"]
                for user in (analyst, viewer):
                    await client.get("/api/v1/workspaces", headers=headers(user))
                for user, role in ((analyst, "analyst"), (viewer, "viewer")):
                    response = await client.post(
                        f"/api/v1/workspaces/{workspace}/members",
                        headers=headers(owner),
                        json={"user_id": str(user), "role": role},
                    )
                    assert response.status_code == 204

                invalid_payloads = [
                    {"name": "   "},
                    {"name": "Bad URL", "website_url": "example.test"},
                    {"name": "Credentials", "website_url": "https://a:b@example.test"},
                    {"name": "Country", "country_code": "USA"},
                    {"name": "X" * 201},
                    {"name": "Unexpected", "workspace_id": workspace},
                ]
                for payload in invalid_payloads:
                    response = await client.post(
                        f"/api/v1/workspaces/{workspace}/companies",
                        headers=headers(analyst),
                        json=payload,
                    )
                    assert response.status_code == 422

                denied = await client.post(
                    f"/api/v1/workspaces/{workspace}/companies",
                    headers=headers(viewer),
                    json={"name": "Viewer write"},
                )
                assert denied.status_code == 403

                payloads = [
                    {
                        "name": "O'Reilly 100%_日本",
                        "website_url": "https://example.test/path?private=value",
                        "industry": "Software_100%",
                        "country_code": "lk",
                        "description": "Full record",
                        "notes": "private text",
                    },
                    {"name": "Plain company", "industry": "Services", "country_code": "US"},
                ]
                created = []
                for payload in payloads:
                    response = await client.post(
                        f"/api/v1/workspaces/{workspace}/companies",
                        headers=headers(analyst),
                        json=payload,
                    )
                    assert response.status_code == 201
                    created.append(response.json())
                assert created[0]["created_by"] == str(analyst)
                assert created[0]["country_code"] == "LK"

                list_response = await client.get(
                    f"/api/v1/workspaces/{workspace}/companies",
                    headers=headers(viewer),
                    params={"limit": 1},
                )
                assert list_response.status_code == 200
                first_page = list_response.json()
                assert len(first_page["items"]) == 1
                assert "notes" not in first_page["items"][0]
                assert first_page["next_cursor"]
                second_page = await client.get(
                    f"/api/v1/workspaces/{workspace}/companies",
                    headers=headers(viewer),
                    params={"limit": 1, "cursor": first_page["next_cursor"]},
                )
                assert second_page.status_code == 200
                assert second_page.json()["items"][0]["id"] != first_page["items"][0]["id"]
                cursor_mismatch = await client.get(
                    f"/api/v1/workspaces/{workspace}/companies",
                    headers=headers(viewer),
                    params={"cursor": first_page["next_cursor"], "search": "Plain"},
                )
                assert cursor_mismatch.status_code == 400

                for search in ("O'Reilly", "%", "_", "日本"):
                    response = await client.get(
                        f"/api/v1/workspaces/{workspace}/companies",
                        headers=headers(viewer),
                        params={"search": search},
                    )
                    assert [item["id"] for item in response.json()["items"]] == [created[0]["id"]]
                industry = await client.get(
                    f"/api/v1/workspaces/{workspace}/companies",
                    headers=headers(viewer),
                    params={"industry": "software_100%", "country_code": "lk"},
                )
                assert [item["id"] for item in industry.json()["items"]] == [created[0]["id"]]

                detail_path = f"/api/v1/workspaces/{workspace}/companies/{created[0]['id']}"
                changed = await client.patch(
                    detail_path,
                    headers=headers(analyst),
                    json={"expected_version": 1, "description": "Changed only"},
                )
                assert changed.status_code == 200
                assert changed.json()["industry"] == "Software_100%"
                assert changed.json()["version"] == 2
                cleared = await client.patch(
                    detail_path,
                    headers=headers(analyst),
                    json={"expected_version": 2, "industry": None},
                )
                assert cleared.json()["industry"] is None
                assert cleared.json()["version"] == 3
                stale = await client.patch(
                    detail_path,
                    headers=headers(analyst),
                    json={"expected_version": 2, "name": "Stale"},
                )
                assert stale.status_code == 409
                assert stale.json()["detail"]["code"] == "version_conflict"

                archived = await client.post(
                    f"{detail_path}/archive",
                    headers=headers(analyst),
                    json={"expected_version": 3},
                )
                assert archived.status_code == 200
                assert archived.json()["id"] == created[0]["id"]
                assert archived.json()["version"] == 4
                active = await client.get(
                    f"/api/v1/workspaces/{workspace}/companies", headers=headers(viewer)
                )
                assert created[0]["id"] not in {item["id"] for item in active.json()["items"]}
                archived_list = await client.get(
                    f"/api/v1/workspaces/{workspace}/companies",
                    headers=headers(viewer),
                    params={"archive": "archived"},
                )
                assert [item["id"] for item in archived_list.json()["items"]] == [created[0]["id"]]
                restored = await client.post(
                    f"{detail_path}/restore",
                    headers=headers(analyst),
                    json={"expected_version": 4},
                )
                assert restored.json()["id"] == created[0]["id"]
                assert restored.json()["archived_at"] is None
        finally:
            await app.state.database.dispose()
            await admin_engine.dispose()

    asyncio.run(scenario())
