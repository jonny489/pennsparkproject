"""Test fixtures.

Routes are exercised against an in-memory repository rather than Postgres. No
Supabase project is connected yet, and keeping the DB out of the loop makes the
suite fast and hermetic. The fake mirrors the real repository's ownership
semantics so the isolation tests are meaningful.
"""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth import get_current_user_id
from app.config import get_settings
from app.db import get_repository
from app.main import create_app
from app.models import ItemCreate, ItemRead, MediaType, Status

USER_A = UUID("11111111-1111-1111-1111-111111111111")
USER_B = UUID("22222222-2222-2222-2222-222222222222")


class FakeItemRepository:
    """In-memory ItemRepository, keyed by (user_id, item_id).

    Keying on the owner means a lookup for the wrong user misses naturally,
    exactly as the SQL `where user_id = $1` does.
    """

    def __init__(self) -> None:
        self._items: dict[tuple[UUID, UUID], ItemRead] = {}

    async def list_items(
        self,
        user_id: UUID,
        *,
        search: str | None = None,
        media_type: MediaType | None = None,
        status: Status | None = None,
    ) -> list[ItemRead]:
        results = [item for (owner, _), item in self._items.items() if owner == user_id]
        if search:
            results = [i for i in results if search.lower() in i.title.lower()]
        if media_type is not None:
            results = [i for i in results if i.media_type is media_type]
        if status is not None:
            results = [i for i in results if i.status is status]
        return sorted(results, key=lambda i: i.created_at, reverse=True)

    async def get_item(self, user_id: UUID, item_id: UUID) -> ItemRead | None:
        return self._items.get((user_id, item_id))

    async def create_item(self, user_id: UUID, data: ItemCreate) -> ItemRead:
        now = datetime.now(timezone.utc)
        item = ItemRead(
            id=uuid4(),
            title=data.title,
            creator=data.creator,
            media_type=data.media_type,
            status=data.status,
            rating=data.rating,
            created_at=now,
            updated_at=now,
        )
        self._items[(user_id, item.id)] = item
        return item

    async def update_item(
        self, user_id: UUID, item_id: UUID, changes: dict[str, object]
    ) -> ItemRead | None:
        existing = self._items.get((user_id, item_id))
        if existing is None:
            return None
        merged = existing.model_dump()
        merged.update(changes)
        merged["updated_at"] = datetime.now(timezone.utc)
        updated = ItemRead.model_validate(merged)
        self._items[(user_id, item_id)] = updated
        return updated

    async def delete_item(self, user_id: UUID, item_id: UUID) -> bool:
        return self._items.pop((user_id, item_id), None) is not None


class CurrentUser:
    """Mutable holder so a test can switch identity mid-test."""

    def __init__(self, user_id: UUID) -> None:
        self.id = user_id


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Pin settings for every test.

    get_settings is lru_cached, so the cache is cleared on both sides to stop
    one test's environment from leaking into the next.
    """
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("ALLOW_DEV_USER_HEADER", "false")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def repo() -> FakeItemRepository:
    return FakeItemRepository()


@pytest.fixture
def current_user() -> CurrentUser:
    return CurrentUser(USER_A)


@pytest.fixture
def app(repo: FakeItemRepository, current_user: CurrentUser) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_repository] = lambda: repo
    application.dependency_overrides[get_current_user_id] = lambda: current_user.id
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # ASGITransport skips the lifespan, so no database pool is opened.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def unauthenticated_client(repo: FakeItemRepository) -> AsyncIterator[AsyncClient]:
    """App with real auth in place, to prove endpoints are actually guarded."""
    application = create_app()
    application.dependency_overrides[get_repository] = lambda: repo
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as ac:
        yield ac
