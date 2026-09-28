from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from arizonix_api.auth.dependencies import CurrentPrincipal


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    email: str | None


router = APIRouter(tags=["identity"])


@router.get("/me", response_model=MeResponse)
async def read_me(principal: CurrentPrincipal, response: Response) -> MeResponse:
    response.headers["Cache-Control"] = "no-store"
    return MeResponse(user_id=principal.user_id, email=principal.email)
