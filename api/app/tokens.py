"""Issuing and reading the tokens this API signs itself."""

import datetime
from typing import Any
from uuid import UUID

import jwt

from app.config import Settings

ALGORITHM = "HS256"
TOKEN_TTL = datetime.timedelta(days=7)
STATE_TTL = datetime.timedelta(minutes=10)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def create_access_token(user_id: UUID, email: str, settings: Settings) -> str:
    now = _now()
    return jwt.encode(
        {"sub": str(user_id), "email": email, "iat": now, "exp": now + TOKEN_TTL},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError on failure. The pinned algorithm list is
    what refuses a token claiming alg=none."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def sign_state(settings: Settings) -> str:
    """Short-lived CSRF token for the OAuth round trip. Signing it avoids
    needing a server-side store of in-flight sign-ins."""
    now = _now()
    return jwt.encode(
        {"purpose": "oauth-state", "iat": now, "exp": now + STATE_TTL},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def verify_state(state: str, settings: Settings) -> None:
    """Raises jwt.InvalidTokenError if we did not issue this state."""
    claims = jwt.decode(state, settings.jwt_secret, algorithms=[ALGORITHM])
    if claims.get("purpose") != "oauth-state":
        raise jwt.InvalidTokenError("state has the wrong purpose")
