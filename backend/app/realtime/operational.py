import logging
from dataclasses import dataclass

from pydantic import JsonValue

from app.realtime.broadcaster import event_broadcaster
from app.realtime.events import create_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingRealtimeEvent:
    type: str
    resource_id: str
    data: dict[str, JsonValue]


@dataclass(frozen=True)
class CommittedOperation[ResultT]:
    result: ResultT
    events: tuple[PendingRealtimeEvent, ...] = ()


def telemetry_updated_event(
    *,
    sensor_id: str,
    machine_id: str,
) -> PendingRealtimeEvent:
    return PendingRealtimeEvent(
        type="telemetry.updated",
        resource_id=sensor_id,
        data={
            "sensor_id": sensor_id,
            "machine_id": machine_id,
        },
    )


def alert_event(
    *,
    event_type: str,
    alert_id: str,
    machine_id: str,
    status: str,
) -> PendingRealtimeEvent:
    return PendingRealtimeEvent(
        type=event_type,
        resource_id=alert_id,
        data={
            "alert_id": alert_id,
            "machine_id": machine_id,
            "status": status,
        },
    )


async def publish_committed_events(
    events: tuple[PendingRealtimeEvent, ...],
) -> None:
    for pending_event in events:
        try:
            await event_broadcaster.publish(
                create_event(
                    pending_event.type,
                    resource_id=pending_event.resource_id,
                    data=pending_event.data,
                )
            )
        except Exception:
            logger.exception(
                "Failed to publish committed realtime event %s",
                pending_event.type,
            )
