"""CRUD endpoints for media items."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_current_user_id
from app.db import get_repository
from app.models import (
    ItemCreate,
    ItemRead,
    ItemUpdate,
    MediaType,
    Status,
    validate_rating_rule,
)
from app.repository import ItemRepository

router = APIRouter(prefix="/items", tags=["items"])

# Absent and not-yours both surface as 404. A 403 would confirm that an id
# exists, which leaks the shape of other users' collections.
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.get("", response_model=list[ItemRead])
async def list_items(
    search: str | None = Query(default=None, max_length=200, description="Title contains"),
    media_type: MediaType | None = Query(default=None),
    status_filter: Status | None = Query(default=None, alias="status"),
    user_id: UUID = Depends(get_current_user_id),
    repo: ItemRepository = Depends(get_repository),
) -> list[ItemRead]:
    return await repo.list_items(
        user_id, search=search, media_type=media_type, status=status_filter
    )


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItemRepository = Depends(get_repository),
) -> ItemRead:
    return await repo.create_item(user_id, data)


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItemRepository = Depends(get_repository),
) -> ItemRead:
    item = await repo.get_item(user_id, item_id)
    if item is None:
        raise _NOT_FOUND
    return item


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: UUID,
    data: ItemUpdate,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItemRepository = Depends(get_repository),
) -> ItemRead:
    existing = await repo.get_item(user_id, item_id)
    if existing is None:
        raise _NOT_FOUND

    changes = data.changes()

    # Validate the state the item will END UP in, not the patch body. Checking
    # the body alone would accept {"status": "planned"} against a completed item
    # that already carries a rating, leaving an invalid row behind.
    merged_status = changes.get("status", existing.status)
    merged_rating = changes.get("rating", existing.rating)
    try:
        validate_rating_rule(Status(merged_status), merged_rating)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    updated = await repo.update_item(user_id, item_id, changes)
    if updated is None:
        # Deleted between the read and the write.
        raise _NOT_FOUND
    return updated


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repo: ItemRepository = Depends(get_repository),
) -> None:
    if not await repo.delete_item(user_id, item_id):
        raise _NOT_FOUND
