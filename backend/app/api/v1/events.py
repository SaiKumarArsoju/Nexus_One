from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.realtime import (
    RealtimeEvent,
    create_event,
    event_broadcaster,
    event_stream,
)
from app.schemas import TestEventPublishRequest

router = APIRouter(prefix="/api/v1", tags=["Events"])


@router.get("/events/stream")
def stream_realtime_events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/events/test",
    response_model=RealtimeEvent,
)
async def publish_test_event(
    request: TestEventPublishRequest,
) -> RealtimeEvent:
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    event = create_event(
        request.type,
        resource_id=request.resource_id,
        data=request.data,
    )
    await event_broadcaster.publish(event)
    return event
