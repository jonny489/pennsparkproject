"""The in-memory user repository the route tests depend on.

The Postgres implementation needs a database, so this checks the fake honours
the same contract the routes rely on.
"""

from tests.conftest import FakeUserRepository


async def test_a_created_user_is_findable_by_email(users: FakeUserRepository) -> None:
    created = await users.create_user("a@example.com", password_hash="x")
    found = await users.get_by_email("a@example.com")
    assert found is not None and found.id == created.id


async def test_email_lookup_ignores_case(users: FakeUserRepository) -> None:
    """schema.sql stores email as citext, so the fake must match that."""
    created = await users.create_user("Person@Example.com", password_hash="x")
    found = await users.get_by_email("person@example.com")
    assert found is not None and found.id == created.id


async def test_an_unknown_email_returns_none(users: FakeUserRepository) -> None:
    assert await users.get_by_email("nobody@example.com") is None


async def test_a_google_user_is_findable_by_sub(users: FakeUserRepository) -> None:
    created = await users.create_user("g@example.com", google_sub="google-123")
    found = await users.get_by_google_sub("google-123")
    assert found is not None and found.id == created.id


async def test_linking_google_keeps_the_existing_password(
    users: FakeUserRepository,
) -> None:
    created = await users.create_user("a@example.com", password_hash="x")
    linked = await users.link_google(created.id, "google-456")
    assert linked.google_sub == "google-456"
    assert linked.password_hash == "x"
