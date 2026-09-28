import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arizonix_api.auth.verifier import AccessTokenVerifier, build_token_verifier
from arizonix_api.config import Settings, get_settings
from arizonix_api.routers.health import create_health_router
from arizonix_api.routers.identity import router as identity_router


def create_app(
    settings: Settings | None = None,
    *,
    token_verifier: AccessTokenVerifier | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    logging.getLogger().setLevel(active_settings.log_level.upper())
    app = FastAPI(
        title="Arizonix Intelligence API",
        version=active_settings.app_version,
        debug=active_settings.app_environment == "development",
    )
    app.state.token_verifier = token_verifier or build_token_verifier(active_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Authorization"],
    )
    app.include_router(
        create_health_router(version=active_settings.app_version),
        prefix="/api/v1",
    )
    app.include_router(identity_router, prefix="/api/v1")
    return app


app = create_app()
