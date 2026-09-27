from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arizonix_api import __version__
from arizonix_api.config import Settings, get_settings
from arizonix_api.routers.health import create_health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(title="Arizonix Intelligence API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept"],
    )
    app.include_router(create_health_router(version=__version__), prefix="/api/v1")
    return app


app = create_app()
