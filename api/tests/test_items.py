"""Endpoint tests for the items API."""

from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from tests.conftest import USER_B, CurrentUser

BOOK: dict[str, Any] = {
    "title": "Piranesi",
    "creator": "Susanna Clarke",
    "media_type": "book",
}


async def _create(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/items", json={**BOOK, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


async def test_health_needs_no_auth(unauthenticated_client: AsyncClient) -> None:
    response = await unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_then_read_round_trip(client: AsyncClient) -> None:
    created = await _create(client)
    assert created["title"] == "Piranesi"
    assert created["status"] == "planned"
    assert created["rating"] is None

    fetched = await client.get(f"/items/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


async def test_update_and_delete(client: AsyncClient) -> None:
    created = await _create(client)

    patched = await client.patch(
        f"/items/{created['id']}", json={"status": "completed", "rating": 5}
    )
    assert patched.status_code == 200
    assert patched.json()["rating"] == 5

    deleted = await client.delete(f"/items/{created['id']}")
    assert deleted.status_code == 204

    assert (await client.get(f"/items/{created['id']}")).status_code == 404


async def test_title_is_trimmed_and_blank_is_rejected(client: AsyncClient) -> None:
    created = await _create(client, title="  Dune  ")
    assert created["title"] == "Dune"

    blank = await client.post("/items", json={**BOOK, "title": "   "})
    assert blank.status_code == 422

    blank_creator = await client.post("/items", json={**BOOK, "creator": ""})
    assert blank_creator.status_code == 422


async def test_rating_requires_completed_on_create(client: AsyncClient) -> None:
    response = await client.post("/items", json={**BOOK, "status": "planned", "rating": 4})
    assert response.status_code == 422


async def test_rating_out_of_range_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/items", json={**BOOK, "status": "completed", "rating": 6}
    )
    assert response.status_code == 422


async def test_patch_cannot_strand_a_rating_on_an_unfinished_item(
    client: AsyncClient,
) -> None:
    """The merge-validation case: the body alone looks fine, the result does not.

    Moving a rated, completed item back to 'planned' would leave a rating
    attached to something the user has not finished.
    """
    created = await _create(client, status="completed", rating=4)

    response = await client.patch(f"/items/{created['id']}", json={"status": "planned"})
    assert response.status_code == 422

    # Clearing the rating in the same request is the valid way to do it.
    ok = await client.patch(
        f"/items/{created['id']}", json={"status": "planned", "rating": None}
    )
    assert ok.status_code == 200
    assert ok.json()["rating"] is None
    assert ok.json()["status"] == "planned"


async def test_patch_with_no_fields_leaves_item_unchanged(client: AsyncClient) -> None:
    """An empty body must not be read as 'clear every field'."""
    created = await _create(client)
    response = await client.patch(f"/items/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json()["title"] == created["title"]
    assert response.json()["media_type"] == created["media_type"]


async def test_search_and_filters_narrow_results(client: AsyncClient) -> None:
    await _create(client, title="Piranesi", media_type="book")
    await _create(client, title="Portal", media_type="game", status="completed", rating=5)
    await _create(client, title="Arrival", media_type="movie", status="in_progress")

    assert len((await client.get("/items")).json()) == 3

    # Case-insensitive contains.
    by_search = await client.get("/items", params={"search": "por"})
    assert [i["title"] for i in by_search.json()] == ["Portal"]

    by_type = await client.get("/items", params={"media_type": "movie"})
    assert [i["title"] for i in by_type.json()] == ["Arrival"]

    by_status = await client.get("/items", params={"status": "completed"})
    assert [i["title"] for i in by_status.json()] == ["Portal"]

    combined = await client.get(
        "/items", params={"media_type": "book", "status": "completed"}
    )
    assert combined.json() == []


async def test_unknown_id_is_404(client: AsyncClient) -> None:
    missing = uuid4()
    assert (await client.get(f"/items/{missing}")).status_code == 404
    assert (await client.patch(f"/items/{missing}", json={"title": "x"})).status_code == 404
    assert (await client.delete(f"/items/{missing}")).status_code == 404


async def test_users_cannot_reach_each_others_items(
    client: AsyncClient, current_user: CurrentUser
) -> None:
    """The core ownership invariant.

    FastAPI connects to Postgres with a role that bypasses RLS, so this
    isolation is enforced entirely by the backend's user-scoped queries. If this
    test ever fails, every user's collection is readable by everyone.
    """
    created = await _create(client)

    current_user.id = USER_B

    # 404 rather than 403 — a 403 would confirm the id exists.
    assert (await client.get(f"/items/{created['id']}")).status_code == 404
    assert (
        await client.patch(f"/items/{created['id']}", json={"title": "stolen"})
    ).status_code == 404
    assert (await client.delete(f"/items/{created['id']}")).status_code == 404

    # And it must not show up in their collection listing.
    assert (await client.get("/items")).json() == []


async def test_endpoints_require_a_token(unauthenticated_client: AsyncClient) -> None:
    assert (await unauthenticated_client.get("/items")).status_code == 401
    assert (await unauthenticated_client.post("/items", json=BOOK)).status_code == 401

    bad_token = {"Authorization": "Bearer not-a-real-jwt"}
    rejected = await unauthenticated_client.get("/items", headers=bad_token)
    assert rejected.status_code == 401
    # The failure reason must not echo the token back to the caller.
    assert "not-a-real-jwt" not in rejected.text
