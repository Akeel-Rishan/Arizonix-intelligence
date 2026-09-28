from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from arizonix_api.db.session import authenticated_session

AuthenticatedSession = Annotated[AsyncSession, Depends(authenticated_session)]
