import asyncio
import json
from datetime import UTC

import pytest
from app.core.config import settings
from app.realtime import (
    EventBroadcaster,
    create_event,
    event_broadcaster,
    event_stream,
    format_heartbeat,
    format_sse_event,
)


class DisconnectSequence:
    def __init__(self, *states: bool) -> None:
        self._states = iter(states)

    async def is_disconnected(self) -> bool:
        return next(self._states, True)


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


def test_event_creation_generates_unique_id_and_utc_timestamp():
    first = create_event(
        "system.test",
        resource_id="machine-1",
        data={"message": "hello"},
    )
    second = create_event("system.test")

    assert first.id != second.id
    assert first.type == "system.test"
    assert first.resource_id == "machine-1"
    assert first.data == {"message": "hello"}
    assert first.occurred_at.tzinfo is not None
    assert first.occurred_at.utcoffset() == UTC.utcoffset(first.occurred_at)


def test_subscribe_publish_and_unsubscribe():
    async def scenario() -> None:
        broadcaster = EventBroadcaster()
        queue = broadcaster.subscribe()
        first = create_event("system.first")

        await broadcaster.publish(first)

        assert await queue.get() == first
        assert broadcaster.subscriber_count == 1

        broadcaster.unsubscribe(queue)
        await broadcaster.publish(create_event("system.second"))

        assert broadcaster.subscriber_count == 0
        assert queue.empty()

    asyncio.run(scenario())


def test_multiple_subscribers_receive_same_event_independently():
    async def scenario() -> None:
        broadcaster = EventBroadcaster()
        first_queue = broadcaster.subscribe()
        second_queue = broadcaster.subscribe()
        event = create_event("system.broadcast")

        await broadcaster.publish(event)

        assert await first_queue.get() == event
        assert await second_queue.get() == event
        assert first_queue is not second_queue

    asyncio.run(scenario())


def test_bounded_queue_drops_oldest_and_retains_newest_event():
    async def scenario() -> None:
        broadcaster = EventBroadcaster(queue_size=2)
        queue = broadcaster.subscribe()
        events = [
            create_event("system.first"),
            create_event("system.second"),
            create_event("system.third"),
        ]

        for event in events:
            await broadcaster.publish(event)

        assert queue.maxsize == 2
        assert queue.qsize() == 2
        assert await queue.get() == events[1]
        assert await queue.get() == events[2]

    asyncio.run(scenario())


def test_development_test_endpoint_publishes_and_returns_event(
    client,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "development")
    queue = event_broadcaster.subscribe()

    try:
        response = client.post(
            "/api/v1/events/test",
            json={
                "type": "system.test",
                "resource_id": "machine-1",
                "data": {"message": "hello"},
            },
        )
        published = queue.get_nowait()
    finally:
        event_broadcaster.unsubscribe(queue)

    assert response.status_code == 200
    assert response.json() == published.model_dump(mode="json")
    assert published.type == "system.test"
    assert published.resource_id == "machine-1"
    assert published.data == {"message": "hello"}


@pytest.mark.parametrize(
    "event_type",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace"),
        pytest.param("telemetry.updated", id="non-system-prefix"),
        pytest.param("system.bad event", id="invalid-characters"),
    ],
)
def test_development_test_endpoint_rejects_invalid_event_type(
    client,
    monkeypatch,
    event_type,
):
    monkeypatch.setattr(settings, "environment", "development")

    response = client.post(
        "/api/v1/events/test",
        json={"type": event_type},
    )

    assert response.status_code == 422


def test_test_publish_endpoint_is_unavailable_outside_development(
    client,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "production")

    response = client.post(
        "/api/v1/events/test",
        json={"type": "system.test"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_sse_event_format_contains_required_fields_and_blank_line():
    event = create_event(
        "system.test",
        resource_id="machine-1",
        data={"message": "hello"},
    )

    frame = format_sse_event(event)
    lines = frame.splitlines()
    data = json.loads(lines[2].removeprefix("data: "))

    assert lines[0] == f"id: {event.id}"
    assert lines[1] == "event: system.test"
    assert data == event.model_dump(mode="json")
    assert frame.endswith("\n\n")


def test_heartbeat_is_valid_sse_comment_frame():
    assert format_heartbeat() == ": heartbeat\n\n"


def test_event_stream_emits_connected_event_and_published_event():
    async def scenario() -> None:
        broadcaster = EventBroadcaster()
        stream = event_stream(
            ConnectedRequest(),
            broadcaster=broadcaster,
            heartbeat_interval=1.0,
        )

        connected_frame = await anext(stream)
        event = create_event("system.test")
        await broadcaster.publish(event)
        published_frame = await anext(stream)
        await stream.aclose()

        assert "event: system.connected\n" in connected_frame
        assert published_frame == format_sse_event(event)
        assert broadcaster.subscriber_count == 0

    asyncio.run(scenario())


def test_event_stream_emits_heartbeat_without_timing_delay():
    async def scenario() -> None:
        broadcaster = EventBroadcaster()
        stream = event_stream(
            ConnectedRequest(),
            broadcaster=broadcaster,
            heartbeat_interval=0.001,
        )

        await anext(stream)
        heartbeat = await anext(stream)
        await stream.aclose()

        assert heartbeat == format_heartbeat()
        assert broadcaster.subscriber_count == 0

    asyncio.run(scenario())


def test_disconnect_unsubscribes_stream_queue():
    async def scenario() -> None:
        broadcaster = EventBroadcaster()
        stream = event_stream(
            DisconnectSequence(False, True),
            broadcaster=broadcaster,
        )

        await anext(stream)
        assert broadcaster.subscriber_count == 1

        with pytest.raises(StopAsyncIteration):
            await anext(stream)

        assert broadcaster.subscriber_count == 0

    asyncio.run(scenario())
