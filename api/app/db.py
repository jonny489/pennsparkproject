"""Connection pool lifecycle and the repository dependency."""

import asyncpg

from app.config import get_settings
from app.repository import ItemRepository, PostgresItemRepository

# Held at module level and created once during app startup. asyncpg pools are
# safe to share across requests; opening one per request would be very slow.
_pool: asyncpg.Pool | None = None


async def open_pool() -> None:
    """Create the pool. Fails loudly if DATABASE_URL is missing."""
    global _pool
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy api/.env.example to api/.env and fill in "
            "the Supabase Postgres connection string."
        )
    _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_repository() -> ItemRepository:
    """FastAPI dependency. Tests override this with an in-memory fake."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised; app startup did not run.")
    return PostgresItemRepository(_pool)
