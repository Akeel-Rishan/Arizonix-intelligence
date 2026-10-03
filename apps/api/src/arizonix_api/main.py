import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from arizonix_api.auth.verifier import AccessTokenVerifier, build_token_verifier
from arizonix_api.config import Settings, get_settings
from arizonix_api.db.session import build_database
from arizonix_api.logging.structured import configure_safe_access_logging, log_security_event
from arizonix_api.routers.audit import router as audit_router
from arizonix_api.routers.companies import router as companies_router
from arizonix_api.routers.health import create_health_router
from arizonix_api.routers.identity import router as identity_router
from arizonix_api.routers.memberships import router as memberships_router
from arizonix_api.routers.workspaces import router as workspaces_router
from arizonix_api.services.errors import (
    ApplicationUserNotFound,
    AuditEventNotFound,
    AuditPersistenceFailure,
    CompanyLifecycleConflict,
    CompanyNotFound,
    DuplicateMembership,
    InvalidAuditQuery,
    InvalidCompanyQuery,
    LastOwnerConflict,
    MembershipNotFound,
    PermissionDenied,
    VersionConflict,
    WorkspaceNotFound,
    WorkspaceServiceError,
)

ERROR_DETAILS: dict[type[WorkspaceServiceError], tuple[int, str]] = {
    WorkspaceNotFound: (404, "Workspace not found"),
    MembershipNotFound: (404, "Membership not found"),
    ApplicationUserNotFound: (404, "Application user not found"),
    PermissionDenied: (403, "You do not have permission for this operation"),
    DuplicateMembership: (409, "The user is already a member of this workspace"),
    LastOwnerConflict: (409, "A workspace must keep at least one owner"),
    AuditEventNotFound: (404, "Audit event not found"),
    InvalidAuditQuery: (400, "The audit query is invalid"),
    AuditPersistenceFailure: (500, "The workspace change could not be safely recorded"),
    CompanyNotFound: (404, "Company not found"),
    VersionConflict: (409, "This company changed since you opened it. Refresh and try again"),
    CompanyLifecycleConflict: (409, "Archived companies must be restored before editing"),
    InvalidCompanyQuery: (400, "The company query is invalid"),
}


def create_app(
    settings: Settings | None = None,
    *,
    token_verifier: AccessTokenVerifier | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    database = build_database(active_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if database is not None:
            await database.dispose()

    logging.getLogger().setLevel(active_settings.log_level.upper())
    configure_safe_access_logging()
    app = FastAPI(
        title="Arizonix Intelligence API",
        version=active_settings.app_version,
        debug=active_settings.app_environment == "development",
        lifespan=lifespan,
    )
    app.state.token_verifier = token_verifier or build_token_verifier(active_settings)
    app.state.database = database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Accept", "Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    @app.exception_handler(WorkspaceServiceError)
    async def handle_workspace_error(
        request: Request, error: WorkspaceServiceError
    ) -> JSONResponse:
        error_status, message = ERROR_DETAILS.get(type(error), (500, "Workspace operation failed"))
        log_fields = {
            WorkspaceNotFound: ("security.authorization_denied", "workspace_inaccessible"),
            PermissionDenied: ("security.authorization_denied", "insufficient_role"),
            LastOwnerConflict: ("security.authorization_denied", "last_owner_protection"),
            AuditPersistenceFailure: ("audit.persistence_failed", "required_audit_write_failed"),
        }.get(type(error))
        if log_fields is not None:
            log_security_event(
                request,
                event=log_fields[0],
                reason=log_fields[1],
                status_code=error_status,
                actor_user_id=getattr(request.state, "verified_actor_id", None),
                severity=logging.ERROR
                if isinstance(error, AuditPersistenceFailure)
                else logging.WARNING,
            )
        return JSONResponse(
            status_code=error_status,
            content={"detail": {"code": error.code, "message": message}},
        )

    app.include_router(
        create_health_router(version=active_settings.app_version),
        prefix="/api/v1",
    )
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(workspaces_router, prefix="/api/v1")
    app.include_router(memberships_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(companies_router, prefix="/api/v1")
    return app


app = create_app()
