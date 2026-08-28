from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, JsonValue, StringConstraints

EventType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]


class RealtimeEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: EventType
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    resource_id: str | None = None
    data: dict[str, JsonValue] | None = None


def create_event(
    event_type: str,
    *,
    resource_id: str | None = None,
    data: dict[str, JsonValue] | None = None,
) -> RealtimeEvent:
    return RealtimeEvent(
        type=event_type,
        resource_id=resource_id,
        data=data,
    )
