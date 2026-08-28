from typing import Annotated

from pydantic import BaseModel, JsonValue, StringConstraints

SystemTestEventType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^system\.[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
OptionalResourceId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]


class TestEventPublishRequest(BaseModel):
    type: SystemTestEventType
    resource_id: OptionalResourceId | None = None
    data: dict[str, JsonValue] | None = None
