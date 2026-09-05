"""Registration, login and the current-user endpoint."""

from httpx import AsyncClient

from tests.conftest import FakeUserRepository

CREDENTIALS = {"email": "person@example.com", "password": "a-good-password"}


async def test_register_returns_a_token_and_the_user(
    unauthenticated_client: AsyncClient,
) -> None:
    response = await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "person@example.com"
    assert body["access_token"]


async def test_a_registration_response_never_carries_the_hash(
    unauthenticated_client: AsyncClient,
) -> None:
    response = await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    assert "password" not in response.text
    assert "hash" not in response.text


async def test_a_duplicate_email_is_refused(unauthenticated_client: AsyncClient) -> None:
    await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    again = await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    assert again.status_code == 409


async def test_a_duplicate_email_is_refused_regardless_of_case(
    unauthenticated_client: AsyncClient,
) -> None:
    await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    again = await unauthenticated_client.post(
        "/auth/register", json={**CREDENTIALS, "email": "Person@Example.com"}
    )
    assert again.status_code == 409


async def test_a_short_password_is_refused(unauthenticated_client: AsyncClient) -> None:
    response = await unauthenticated_client.post(
        "/auth/register", json={**CREDENTIALS, "password": "short"}
    )
    assert response.status_code == 422


async def test_login_returns_a_token(unauthenticated_client: AsyncClient) -> None:
    await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    response = await unauthenticated_client.post("/auth/login", json=CREDENTIALS)
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_a_wrong_password_and_an_unknown_email_are_indistinguishable(
    unauthenticated_client: AsyncClient,
) -> None:
    """Different responses would let anyone test which addresses have accounts."""
    await unauthenticated_client.post("/auth/register", json=CREDENTIALS)

    wrong = await unauthenticated_client.post(
        "/auth/login", json={**CREDENTIALS, "password": "wrong-password"}
    )
    unknown = await unauthenticated_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


async def test_a_google_only_account_cannot_log_in_with_a_password(
    unauthenticated_client: AsyncClient, users: FakeUserRepository
) -> None:
    await users.create_user("g@example.com", google_sub="google-1")
    response = await unauthenticated_client.post(
        "/auth/login", json={"email": "g@example.com", "password": "anything"}
    )
    assert response.status_code == 401


async def test_me_returns_the_signed_in_user(
    unauthenticated_client: AsyncClient,
) -> None:
    registered = await unauthenticated_client.post("/auth/register", json=CREDENTIALS)
    token = registered.json()["access_token"]

    response = await unauthenticated_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "person@example.com"


async def test_me_requires_a_token(unauthenticated_client: AsyncClient) -> None:
    assert (await unauthenticated_client.get("/auth/me")).status_code == 401
