"""The Google OAuth round trip, with the token exchange stubbed out."""

import httpx
import jwt
import pytest
from httpx import AsyncClient

from app.config import Settings
from app.routers import auth as auth_router
from app.tokens import sign_state
from tests.conftest import FakeUserRepository

SETTINGS = Settings(jwt_secret="test-secret-not-a-real-key")

VERIFIED = {"sub": "google-abc", "email": "person@example.com", "email_verified": True}


@pytest.fixture(autouse=True)
def google_identity(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Replace the network call to Google with a canned identity.

    Mutate the returned dict's "identity" key to change what Google 'returns'.
    """
    state: dict = {"identity": VERIFIED}

    async def fake_exchange(code: str, settings: Settings) -> dict:
        return state["identity"]

    monkeypatch.setattr(auth_router, "exchange_code", fake_exchange)
    return state


async def _callback(client: AsyncClient):
    return await client.get(
        "/auth/google/callback",
        params={"code": "any", "state": sign_state(SETTINGS)},
        follow_redirects=False,
    )


async def test_the_start_endpoint_redirects_to_google(
    unauthenticated_client: AsyncClient,
) -> None:
    response = await unauthenticated_client.get("/auth/google", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "state=" in location


async def test_the_callback_creates_a_user_and_redirects_with_a_token(
    unauthenticated_client: AsyncClient, users: FakeUserRepository
) -> None:
    response = await _callback(unauthenticated_client)
    assert response.status_code == 307
    # The token rides in the fragment, so it never reaches a server log.
    assert "#token=" in response.headers["location"]
    assert await users.get_by_google_sub("google-abc") is not None


async def test_signing_in_twice_reuses_the_same_account(
    unauthenticated_client: AsyncClient, users: FakeUserRepository
) -> None:
    await _callback(unauthenticated_client)
    await _callback(unauthenticated_client)
    assert len(users.all_users()) == 1


async def test_a_verified_google_email_links_to_an_existing_password_account(
    unauthenticated_client: AsyncClient, users: FakeUserRepository
) -> None:
    existing = await users.create_user("person@example.com", password_hash="x")

    await _callback(unauthenticated_client)

    linked = await users.get_by_id(existing.id)
    assert linked is not None and linked.google_sub == "google-abc"
    assert len(users.all_users()) == 1


async def test_an_unverified_google_email_does_not_link(
    unauthenticated_client: AsyncClient, users: FakeUserRepository, google_identity: dict
) -> None:
    """Linking on an unverified address would let someone claim another
    person's account."""
    await users.create_user("person@example.com", password_hash="x")
    google_identity["identity"] = {**VERIFIED, "email_verified": False}

    response = await _callback(unauthenticated_client)
    # Redirected back to the app with a reason, not raw API JSON in the browser.
    assert response.status_code == 307
    assert "#error=email_taken" in response.headers["location"]
    assert len(users.all_users()) == 1


async def test_a_forged_state_is_rejected(unauthenticated_client: AsyncClient) -> None:
    forged = jwt.encode({"purpose": "oauth-state"}, "not-our-secret", algorithm="HS256")
    response = await unauthenticated_client.get(
        "/auth/google/callback",
        params={"code": "any", "state": forged},
        follow_redirects=False,
    )
    assert response.status_code == 400


async def test_cancelling_at_google_redirects_back_with_a_reason(
    unauthenticated_client: AsyncClient,
) -> None:
    """Google sends error=access_denied and no code when the user cancels."""
    response = await unauthenticated_client.get(
        "/auth/google/callback",
        params={"error": "access_denied", "state": sign_state(SETTINGS)},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "#error=cancelled" in response.headers["location"]


async def test_a_failed_token_exchange_redirects_back_with_a_reason(
    unauthenticated_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expired or reused code, or a Google outage."""

    async def boom(code: str, settings: Settings) -> dict:
        raise httpx.HTTPError("google is unreachable")

    monkeypatch.setattr(auth_router, "exchange_code", boom)

    response = await _callback(unauthenticated_client)
    assert response.status_code == 307
    assert "#error=exchange_failed" in response.headers["location"]


async def test_an_id_token_missing_claims_does_not_500(
    unauthenticated_client: AsyncClient, google_identity: dict
) -> None:
    google_identity["identity"] = {"sub": "google-abc"}  # no email

    response = await _callback(unauthenticated_client)
    assert response.status_code == 307
    assert "#error=exchange_failed" in response.headers["location"]
