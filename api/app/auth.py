"""Turn a bearer token into the caller's user id."""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.tokens import decode_access_token

# auto_error=False so a missing header reaches our handler and gives a
# consistent 401 rather than FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> UUID:
    if credentials is None:
        raise unauthorized("Missing bearer token")

    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured.",
        )

    try:
        claims = decode_access_token(credentials.credentials, settings)
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token has expired") from None
    except jwt.InvalidTokenError as exc:
        raise unauthorized("Token is invalid") from exc

    try:
        return UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise unauthorized("Token subject is missing or malformed") from exc
