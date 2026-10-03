from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arizonix_api.auth.principal import Principal
from arizonix_api.auth.verifier import (
    AccessTokenVerifier,
    AuthenticationServiceUnavailable,
    InvalidAccessToken,
)
from arizonix_api.logging.structured import log_security_event

bearer_scheme = HTTPBearer(auto_error=False)


async def require_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        log_security_event(
            request,
            event="security.authentication_failed",
            reason="missing_bearer_token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    verifier = cast(AccessTokenVerifier, request.app.state.token_verifier)
    try:
        principal = await verifier.verify(credentials.credentials)
        request.state.verified_actor_id = principal.user_id
        return principal
    except InvalidAccessToken as error:
        log_security_event(
            request,
            event="security.authentication_failed",
            reason="invalid_access_token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AuthenticationServiceUnavailable as error:
        log_security_event(
            request,
            event="security.authentication_unavailable",
            reason="token_verification_unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            severity=40,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from error


CurrentPrincipal = Annotated[Principal, Depends(require_principal)]
