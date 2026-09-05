"""Turns a Supabase access token into the caller's user id."""

import logging
import ssl
from functools import lru_cache
from typing import Any
from uuid import UUID

import certifi
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

# auto_error=False so a missing header reaches our handler and produces a
# consistent 401 body instead of FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)

# Supabase stamps this audience on user access tokens.
_AUDIENCE = "authenticated"

# Supabase signs with ES256 (ECC P-256). Pinning the algorithm list is what
# stops a caller from presenting a token that names a weaker algorithm — never
# read the algorithm from the token itself.
_ALGORITHMS = ["ES256"]

_logger = logging.getLogger("shelf.auth")


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    """Trust store for the JWKS fetch.

    PyJWKClient fetches over urllib, which uses whatever CA bundle the Python
    install happens to have. The python.org macOS builds ship without one
    configured, so the fetch dies with CERTIFICATE_VERIFY_FAILED even though
    curl to the same URL succeeds. Pinning certifi's bundle makes the fetch
    behave identically on a laptop and on the deployment host.
    """
    return ssl.create_default_context(cafile=certifi.where())


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    """One client per URL, cached because it holds the fetched key set.

    PyJWKClient looks the token's `kid` up in that set and refetches when it
    sees an unknown one, so key rotation needs no redeploy.
    """
    return jwt.PyJWKClient(jwks_url, cache_keys=True, ssl_context=_ssl_context())


def _resolve_signing_key(token: str, settings: Settings) -> Any:
    """The project's public key matching this token's `kid`."""
    return _jwk_client(settings.jwks_url).get_signing_key_from_jwt(token).key


def _log_verification_failure(token: str, exc: Exception) -> None:
    """Record why a token was refused, without logging the token itself.

    Reads the header and claims WITHOUT verifying the signature, which is safe
    for diagnostics because it only reports metadata we already refused to
    trust. A JWT's header and payload are not secret; only the signature is.
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception:  # noqa: BLE001 - a malformed token has no readable header
        header = {"error": "unreadable header"}

    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        audience, issuer = claims.get("aud"), claims.get("iss")
    except Exception:  # noqa: BLE001 - same
        audience = issuer = "(unreadable)"

    _logger.warning(
        "JWT rejected: %s | token alg=%s kid=%s | expected alg=%s | "
        "token aud=%r expected aud=%r | iss=%s",
        type(exc).__name__,
        header.get("alg"),
        header.get("kid"),
        _ALGORITHMS,
        audience,
        _AUDIENCE,
        issuer,
    )


def _unauthorized(detail: str) -> HTTPException:
    # Detail describes the problem but never echoes token contents back.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> UUID:
    """Verify the bearer token against the project's JWKS and return its subject.

    Local-only escape hatch: when ALLOW_DEV_USER_HEADER is true, an X-Dev-User-Id
    header is trusted instead. It defaults to false and must stay false anywhere
    reachable from the network — it would otherwise let any caller claim any
    identity.
    """
    if settings.allow_dev_user_header:
        dev_user = request.headers.get("X-Dev-User-Id")
        if dev_user:
            try:
                return UUID(dev_user)
            except ValueError as exc:
                raise _unauthorized("X-Dev-User-Id is not a valid UUID") from exc

    if credentials is None:
        raise _unauthorized("Missing bearer token")

    if not settings.supabase_url:
        # Misconfiguration, not a client error: refuse rather than accept tokens
        # we cannot actually verify.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured.",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            _resolve_signing_key(token, settings),
            algorithms=_ALGORITHMS,
            audience=_AUDIENCE,
            issuer=settings.issuer,
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token has expired") from exc
    except jwt.exceptions.PyJWKClientError as exc:
        # The JWKS endpoint was unreachable or had no key for this token's kid.
        _log_verification_failure(token, exc)
        raise _unauthorized("Could not verify the token's signing key") from exc
    except jwt.InvalidTokenError as exc:
        _log_verification_failure(token, exc)
        raise _unauthorized("Token is invalid") from exc

    subject = payload.get("sub")
    if not subject:
        raise _unauthorized("Token is missing a subject claim")

    try:
        return UUID(subject)
    except ValueError as exc:
        raise _unauthorized("Token subject is not a valid UUID") from exc
