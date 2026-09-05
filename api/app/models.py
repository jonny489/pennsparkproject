"""Request and response models, and the one business rule they share."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

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


class UserCreate(BaseModel):
    email: EmailStr
    # 72 bytes is bcrypt's ceiling; 8 is a reasonable floor.
    password: Annotated[str, Field(min_length=8, max_length=72)]


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    """What the API returns. Deliberately has no password_hash field."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime


class UserRecord(BaseModel):
    """Internal row including the hash. Never returned from an endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    password_hash: str | None
    google_sub: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
