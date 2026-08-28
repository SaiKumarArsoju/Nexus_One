import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from app.realtime.broadcaster import (
    EventBroadcaster,
    event_broadcaster,
)
from app.realtime.events import RealtimeEvent, create_event

HEARTBEAT_INTERVAL_SECONDS = 15.0


class DisconnectAware(Protocol):
    async def is_disconnected(self) -> bool: ...


def format_sse_event(event: RealtimeEvent) -> str:
    lines = (
        f"id: {event.id}",
        f"event: {event.type}",
        f"data: {event.model_dump_json()}",
        "",
    )
    return "\n".join(lines) + "\n"


def format_heartbeat() -> str:
    return ": heartbeat\n\n"


async def event_stream(
    request: DisconnectAware,
    *,
    broadcaster: EventBroadcaster = event_broadcaster,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncIterator[str]:
    async with broadcaster.subscription() as queue:
        if await request.is_disconnected():
            return

        yield format_sse_event(create_event("system.connected"))

        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=heartbeat_interval,
                )
            except TimeoutError:
                if not await request.is_disconnected():
                    yield format_heartbeat()
            else:
                yield format_sse_event(event)
