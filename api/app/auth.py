"""Verify a Supabase access token and extract the caller's user id."""

import logging
import ssl
from functools import lru_cache
from typing import Any
from uuid import UUID

import certifi
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_AUDIENCE = "authenticated"

# Pinned, so a caller cannot present a token that names a weaker algorithm.
_ALGORITHMS = ["ES256"]

_logger = logging.getLogger("shelf.auth")


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    # PyJWKClient fetches over urllib, which has no CA bundle on the python.org
    # macOS builds. certifi makes the fetch behave the same everywhere.
    return ssl.create_default_context(cafile=certifi.where())


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    # Cached: it holds the fetched key set and refetches only on an unknown kid.
    return jwt.PyJWKClient(jwks_url, cache_keys=True, ssl_context=_ssl_context())


def _signing_key(token: str, settings: Settings) -> Any:
    """The project's public key matching this token's `kid`."""
    return _jwk_client(settings.jwks_url).get_signing_key_from_jwt(token).key


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _log_rejection(token: str, exc: Exception) -> None:
    """Record why a token was refused. Only the signature is secret, not the claims."""
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        header, claims = {}, {}

    _logger.warning(
        "JWT rejected: %s | alg=%s kid=%s | aud=%r | iss=%s",
        type(exc).__name__,
        header.get("alg"),
        header.get("kid"),
        claims.get("aud"),
        claims.get("iss"),
    )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> UUID:
    """Verify the bearer token against the project's JWKS and return its subject."""
    if credentials is None:
        raise _unauthorized("Missing bearer token")

    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured.",
        )

    token = credentials.credentials
    try:
        claims = jwt.decode(
            token,
            _signing_key(token, settings),
            algorithms=_ALGORITHMS,
            audience=_AUDIENCE,
            issuer=settings.issuer,
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired") from None
    except (jwt.InvalidTokenError, jwt.exceptions.PyJWKClientError) as exc:
        _log_rejection(token, exc)
        raise _unauthorized("Token is invalid") from exc

    try:
        return UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized("Token subject is missing or malformed") from exc
