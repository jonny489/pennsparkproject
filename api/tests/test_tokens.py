"""Access token issuing and verification."""

import datetime
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import auth
from app.config import Settings
from app.tokens import create_access_token

SETTINGS = Settings(jwt_secret="test-secret-not-a-real-key")
USER_ID = uuid4()


def call(token: str):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return auth.get_current_user_id(credentials, SETTINGS)


def test_a_token_we_issued_yields_its_subject() -> None:
    assert call(create_access_token(USER_ID, "a@example.com", SETTINGS)) == USER_ID


def test_a_token_signed_with_another_secret_is_rejected() -> None:
    forged = jwt.encode(
        {
            "sub": str(USER_ID),
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=1),
        },
        "not-our-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        call(forged)
    assert exc.value.status_code == 401


def test_an_expired_token_is_rejected() -> None:
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    expired = jwt.encode(
        {"sub": str(USER_ID), "exp": past}, SETTINGS.jwt_secret, algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        call(expired)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_a_malformed_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        call("not-a-jwt")
    assert exc.value.status_code == 401


def test_an_algorithm_none_token_is_rejected() -> None:
    """The classic JWT attack: an unsigned token claiming alg=none."""
    forged = jwt.encode({"sub": str(USER_ID)}, key="", algorithm="none")
    with pytest.raises(HTTPException) as exc:
        call(forged)
    assert exc.value.status_code == 401
