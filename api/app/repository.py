"""Data access for items.

Every method takes `user_id` first. The service connects to Postgres with a role
that bypasses row level security, so ownership is enforced here, in SQL, and a
leading parameter is hard to forget at a call site.
"""

from typing import Any, Protocol
from uuid import UUID

import asyncpg

from app.models import ItemCreate, ItemRead, MediaType, Status

# Explicit rather than `select *`, which also keeps user_id out of responses.
_COLUMNS = "id, title, creator, media_type, status, rating, created_at, updated_at"

# Columns a PATCH may touch, and the cast each needs. Building the SET clause
# from this table means a column name can never arrive from a request body.
_UPDATABLE = {
    "title": "",
    "creator": "",
    "media_type": "::media_type",
    "status": "::item_status",
    "rating": "",
}


class ItemRepository(Protocol):
    """Storage interface, so routes can be tested against an in-memory fake."""

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
        self, user_id: UUID, item_id: UUID, changes: dict[str, Any]
    ) -> ItemRead | None: ...

    async def delete_item(self, user_id: UUID, item_id: UUID) -> bool: ...


class PostgresItemRepository:
    """asyncpg implementation. Values are always bound, never formatted into SQL."""

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
        params: list[Any] = [user_id]

        if search:
            params.append(f"%{search}%")
            conditions.append(f"title ILIKE ${len(params)}")
        if media_type is not None:
            params.append(media_type.value)
            conditions.append(f"media_type = ${len(params)}::media_type")
        if status is not None:
            params.append(status.value)
            conditions.append(f"status = ${len(params)}::item_status")

        rows = await self._pool.fetch(
            f"select {_COLUMNS} from items where {' and '.join(conditions)} "
            "order by created_at desc",
            *params,
        )
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
        return ItemRead.model_validate(dict(row))

    async def update_item(
        self, user_id: UUID, item_id: UUID, changes: dict[str, Any]
    ) -> ItemRead | None:
        assignments: list[str] = []
        params: list[Any] = []
        for column, cast in _UPDATABLE.items():
            if column in changes:
                params.append(changes[column])
                assignments.append(f"{column} = ${len(params)}{cast}")

        if not assignments:
            # Nothing to write; report current state rather than bumping updated_at.
            return await self.get_item(user_id, item_id)

        params += [item_id, user_id]
        row = await self._pool.fetchrow(
            f"update items set {', '.join(assignments)} "
            f"where id = ${len(params) - 1} and user_id = ${len(params)} "
            f"returning {_COLUMNS}",
            *params,
        )
        return ItemRead.model_validate(dict(row)) if row else None

    async def delete_item(self, user_id: UUID, item_id: UUID) -> bool:
        result = await self._pool.execute(
            "delete from items where id = $1 and user_id = $2", item_id, user_id
        )
        return result.endswith(" 1")  # asyncpg returns a tag like "DELETE 1"
