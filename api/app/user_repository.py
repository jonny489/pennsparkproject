"""Data access for user accounts."""

from typing import Any, Protocol
from uuid import UUID

import asyncpg

from app.models import UserRecord

_COLUMNS = "id, email, password_hash, google_sub, created_at"


class EmailAlreadyRegistered(Exception):
    """Raised when a concurrent request won the race to insert this email."""


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> UserRecord | None: ...

    async def get_by_email(self, email: str) -> UserRecord | None: ...

    async def get_by_google_sub(self, google_sub: str) -> UserRecord | None: ...

    async def create_user(
        self,
        email: str,
        *,
        password_hash: str | None = None,
        google_sub: str | None = None,
    ) -> UserRecord:
        # The caller's existence check and this insert are separate statements,
        # so a concurrent signup can still lose the unique constraint.
        try:
            row = await self._pool.fetchrow(
                f"""
                insert into users (email, password_hash, google_sub)
                values ($1, $2, $3)
                returning {_COLUMNS}
                """,
                email,
                password_hash,
                google_sub,
            )
        except asyncpg.UniqueViolationError as exc:
            raise EmailAlreadyRegistered(email) from exc
        return UserRecord.model_validate(dict(row))

    async def link_google(self, user_id: UUID, google_sub: str) -> UserRecord: ...


class PostgresUserRepository:
    """asyncpg implementation. The email column is citext, so equality is
    already case-insensitive in the database."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def _fetch_one(self, column: str, value: Any) -> UserRecord | None:
        row = await self._pool.fetchrow(
            f"select {_COLUMNS} from users where {column} = $1", value
        )
        return UserRecord.model_validate(dict(row)) if row else None

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        return await self._fetch_one("id", user_id)

    async def get_by_email(self, email: str) -> UserRecord | None:
        return await self._fetch_one("email", email)

    async def get_by_google_sub(self, google_sub: str) -> UserRecord | None:
        return await self._fetch_one("google_sub", google_sub)

    async def create_user(
        self,
        email: str,
        *,
        password_hash: str | None = None,
        google_sub: str | None = None,
    ) -> UserRecord:
        # The existence check in the route and this insert are two statements,
        # so a concurrent signup can still lose the unique constraint.
        try:
            row = await self._pool.fetchrow(
            f"""
            insert into users (email, password_hash, google_sub)
                values ($1, $2, $3)
                returning {_COLUMNS}
                """,
                email,
                password_hash,
                google_sub,
            )
        except asyncpg.UniqueViolationError as exc:
            raise EmailAlreadyRegistered(email) from exc
        return UserRecord.model_validate(dict(row))

    async def link_google(self, user_id: UUID, google_sub: str) -> UserRecord:
        row = await self._pool.fetchrow(
            f"update users set google_sub = $1 where id = $2 returning {_COLUMNS}",
            google_sub,
            user_id,
        )
        return UserRecord.model_validate(dict(row))
