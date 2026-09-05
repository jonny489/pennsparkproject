"""Request and response models, and the one business rule they share."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Trimmed and non-blank, mirroring the CHECK constraints in schema.sql.
NonBlankStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
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
    """A rating only means something once an item is finished."""
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
    """Partial update. The rating rule is checked on the merged result, in the route."""

    title: NonBlankStr | None = None
    creator: NonBlankStr | None = None
    media_type: MediaType | None = None
    status: Status | None = None
    rating: Rating | None = None

    def changes(self) -> dict[str, Any]:
        # exclude_unset separates "field absent" from "explicitly null";
        # mode="json" renders enums as the plain strings the database wants.
        return self.model_dump(exclude_unset=True, mode="json")


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    creator: str
    media_type: MediaType
    status: Status
    rating: int | None
    created_at: datetime
    updated_at: datetime
