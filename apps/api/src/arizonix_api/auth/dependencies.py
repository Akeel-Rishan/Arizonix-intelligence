from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arizonix_api.auth.principal import Principal
from arizonix_api.auth.verifier import (
    AccessTokenVerifier,
    AuthenticationServiceUnavailable,
    InvalidAccessToken,
)

bearer_scheme = HTTPBearer(auto_error=False)


async def require_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    verifier = cast(AccessTokenVerifier, request.app.state.token_verifier)
    try:
        return await verifier.verify(credentials.credentials)
    except InvalidAccessToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AuthenticationServiceUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from error


CurrentPrincipal = Annotated[Principal, Depends(require_principal)]
