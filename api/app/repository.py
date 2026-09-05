"""Data access for items.

Every method takes `user_id` as its first argument. That is deliberate: the
FastAPI service connects to Postgres with a privileged role, which bypasses row
level security, so ownership is enforced here in SQL. Making user_id the leading
parameter of every signature means a call site cannot quietly omit it.
"""

from typing import Protocol
from uuid import UUID

import asyncpg

from app.models import ItemCreate, ItemRead, MediaType, Status

# Never `select *` — an explicit list keeps the response stable if the table
# gains a column, and keeps user_id out of API responses.
_COLUMNS = "id, title, creator, media_type, status, rating, created_at, updated_at"

# Columns a PATCH is allowed to touch, mapped to the cast their type needs.
# Update statements build their SET clause from this table rather than from
# caller-supplied keys, so a column name can never arrive from a request body.
_UPDATABLE: dict[str, str] = {
    "title": "",
    "creator": "",
    "media_type": "::media_type",
    "status": "::item_status",
    "rating": "",
}


class ItemRepository(Protocol):
    """Storage interface for items.

    Routes depend on this Protocol rather than on Postgres directly, so tests
    can substitute an in-memory fake. That matters here because no Supabase
    project is connected yet, so a live database cannot be in the test loop.
    """

    async def list_items(
        self,
        user_id: UUID,
        *,
        search: str | None = None,
        media_type: MediaType | None = None,
        status: Status | None = None,
    ) -> list[ItemRead]: ...

    async def get_item(self, user_id: UUID, item_id: UUID) -> ItemRead | None: ...

    async def create_item(self, user_id: UUID, data: ItemCreate) -> ItemRead: ...

    async def update_item(
        self, user_id: UUID, item_id: UUID, changes: dict[str, object]
    ) -> ItemRead | None: ...

    async def delete_item(self, user_id: UUID, item_id: UUID) -> bool: ...


class PostgresItemRepository:
    """asyncpg-backed implementation.

    All values travel as bound parameters ($1, $2, ...). Placeholder *positions*
    are computed, but no caller-supplied value is ever formatted into SQL text.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_items(
        self,
        user_id: UUID,
        *,
        search: str | None = None,
        media_type: MediaType | None = None,
        status: Status | None = None,
    ) -> list[ItemRead]:
        conditions = ["user_id = $1"]
        params: list[object] = [user_id]

        if search:
            params.append(f"%{search}%")
            # ILIKE for case-insensitive contains; the wildcards are part of the
            # bound value, not the SQL string.
            conditions.append(f"title ILIKE ${len(params)}")

        if media_type is not None:
            params.append(media_type.value)
            conditions.append(f"media_type = ${len(params)}::media_type")

        if status is not None:
            params.append(status.value)
            conditions.append(f"status = ${len(params)}::item_status")

        query = (
            f"select {_COLUMNS} from items "
            f"where {' and '.join(conditions)} "
            "order by created_at desc"
        )
        rows = await self._pool.fetch(query, *params)
        return [ItemRead.model_validate(dict(row)) for row in rows]

    async def get_item(self, user_id: UUID, item_id: UUID) -> ItemRead | None:
        row = await self._pool.fetchrow(
            f"select {_COLUMNS} from items where id = $1 and user_id = $2",
            item_id,
            user_id,
        )
        return ItemRead.model_validate(dict(row)) if row else None

    async def create_item(self, user_id: UUID, data: ItemCreate) -> ItemRead:
        row = await self._pool.fetchrow(
            f"""
            insert into items (user_id, title, creator, media_type, status, rating)
            values ($1, $2, $3, $4::media_type, $5::item_status, $6)
            returning {_COLUMNS}
            """,
            user_id,
            data.title,
            data.creator,
            data.media_type.value,
            data.status.value,
            data.rating,
        )
        # INSERT ... RETURNING always yields a row unless it raised.
        assert row is not None
        return ItemRead.model_validate(dict(row))

    async def update_item(
        self, user_id: UUID, item_id: UUID, changes: dict[str, object]
    ) -> ItemRead | None:
        if not changes:
            # Nothing to write; report current state rather than issuing a no-op
            # UPDATE that would still bump updated_at.
            return await self.get_item(user_id, item_id)

        assignments: list[str] = []
        params: list[object] = []

        for column, cast in _UPDATABLE.items():
            if column not in changes:
                continue
            value = changes[column]
            # Enums arrive as members from Pydantic; the driver wants the value.
            params.append(value.value if isinstance(value, (MediaType, Status)) else value)
            assignments.append(f"{column} = ${len(params)}{cast}")

        if not assignments:
            return await self.get_item(user_id, item_id)

        params.extend([item_id, user_id])
        query = (
            f"update items set {', '.join(assignments)} "
            f"where id = ${len(params) - 1} and user_id = ${len(params)} "
            f"returning {_COLUMNS}"
        )
        row = await self._pool.fetchrow(query, *params)
        return ItemRead.model_validate(dict(row)) if row else None

    async def delete_item(self, user_id: UUID, item_id: UUID) -> bool:
        result = await self._pool.execute(
            "delete from items where id = $1 and user_id = $2", item_id, user_id
        )
        # asyncpg returns a tag like "DELETE 1"; 0 means nothing matched.
        return result.endswith(" 1")
