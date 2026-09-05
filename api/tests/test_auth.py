"""Token verification tests.

Supabase signs access tokens with ES256 asymmetric keys published at the
project's JWKS endpoint, so these tests mint real ES256 tokens with a throwaway
keypair and inject the public key as the resolved signing key.
"""

import datetime
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import auth
from app.config import Settings

ISSUER = "https://project.supabase.co/auth/v1"
SUBJECT = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def keypair() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def settings() -> Settings:
    return Settings(supabase_url="https://project.supabase.co", database_url="")


def make_token(key: ec.EllipticCurvePrivateKey, **overrides: object) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    claims: dict[str, object] = {
        "sub": SUBJECT,
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": now + datetime.timedelta(hours=1),
        "iat": now,
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="ES256")


def call(token: str, settings: Settings) -> UUID:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return auth.get_current_user_id(credentials, settings)


@pytest.fixture(autouse=True)
def resolve_key(monkeypatch: pytest.MonkeyPatch, keypair):
    """Stand in for the network fetch of the project's JWKS."""
    monkeypatch.setattr(
        auth, "_signing_key", lambda token, settings: keypair.public_key()
    )


def test_valid_es256_token_yields_the_subject(keypair, settings) -> None:
    assert call(make_token(keypair), settings) == UUID(SUBJECT)


def test_token_signed_by_a_different_key_is_rejected(settings) -> None:
    impostor = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(HTTPException) as exc:
        call(make_token(impostor), settings)
    assert exc.value.status_code == 401


def test_expired_token_is_rejected(keypair, settings) -> None:
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    with pytest.raises(HTTPException) as exc:
        call(make_token(keypair, exp=past), settings)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_wrong_issuer_is_rejected(keypair, settings) -> None:
    """A token from another Supabase project must not be accepted."""
    with pytest.raises(HTTPException) as exc:
        call(make_token(keypair, iss="https://someone-else.supabase.co/auth/v1"), settings)
    assert exc.value.status_code == 401


def test_wrong_audience_is_rejected(keypair, settings) -> None:
    with pytest.raises(HTTPException) as exc:
        call(make_token(keypair, aud="anon"), settings)
    assert exc.value.status_code == 401
