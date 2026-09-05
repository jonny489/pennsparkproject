"""FastAPI application for Shelf."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import close_pool, open_pool
from app.routers import auth, items


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await open_pool()
    try:
        yield
    finally:
        await close_pool()


def create_app() -> FastAPI:
    """Factory, so tests can build an app without running the DB lifespan."""
    settings = get_settings()
    app = FastAPI(title="Shelf API", version="0.1.0", lifespan=lifespan)

    # The frontend is served from a different origin, so the browser needs
    # explicit permission to call this API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(items.router)
    app.include_router(auth.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Unauthenticated, so the host's health check can reach it."""
        return {"status": "ok"}

    return app


app = create_app()
