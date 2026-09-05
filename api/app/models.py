"""Pydantic models and the validation rules shared by every writer."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Trim on the way in and reject whitespace-only values, so " " never becomes a
# title. Mirrors the CHECK constraints in schema.sql.
NonBlankStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]

Rating = Annotated[int, Field(ge=1, le=5)]


class MediaType(str, Enum):
    BOOK = "book"
    MOVIE = "movie"
    GAME = "game"


class Status(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


def validate_rating_rule(status: Status, rating: int | None) -> None:
    """A rating only means something once an item is finished.

    Raised as ValueError so Pydantic surfaces it as a 422 rather than a 500.
    Lives in one place because both creates and merged patches must enforce it.
    """
    if rating is not None and status is not Status.COMPLETED:
        raise ValueError("rating can only be set when status is 'completed'")


class ItemCreate(BaseModel):
    title: NonBlankStr
    creator: NonBlankStr
    media_type: MediaType
    status: Status = Status.PLANNED
    rating: Rating | None = None

    @model_validator(mode="after")
    def _check_rating(self) -> Self:
        validate_rating_rule(self.status, self.rating)
        return self


class ItemUpdate(BaseModel):
    """Partial update. Every field is optional.

    This model deliberately does NOT validate the rating rule on its own: a body
    like {"status": "planned"} is valid in isolation but may still produce an
    invalid row once merged onto the stored item. The route merges first, then
    validates the result via `merged_item`.
    """

    title: NonBlankStr | None = None
    creator: NonBlankStr | None = None
    media_type: MediaType | None = None
    status: Status | None = None
    rating: Rating | None = None

    def changes(self) -> dict[str, object]:
        """Only the fields the caller actually sent.

        exclude_unset is what separates "field absent" from "explicitly null" —
        without it, every omitted field would read as an instruction to clear.
        """
        return self.model_dump(exclude_unset=True)


class ItemRead(BaseModel):
    # from_attributes lets this be built straight from an asyncpg Record.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    creator: str
    media_type: MediaType
    status: Status
    rating: int | None
    created_at: datetime
    updated_at: datetime
