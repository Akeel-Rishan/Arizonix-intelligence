from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["arizonix-api"]
    version: str


def create_health_router(*, version: str) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=HealthResponse)
    def get_health() -> HealthResponse:
        """Report process liveness without checking external dependencies."""
        return HealthResponse(status="ok", service="arizonix-api", version=version)

    return router
