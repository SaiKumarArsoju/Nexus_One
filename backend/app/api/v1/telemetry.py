from typing import Annotated
from uuid import UUID

from anyio import from_thread
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.domain.alert_rules import AlertThresholdConfigurationError
from app.realtime import publish_committed_events
from app.schemas import (
    TelemetryIngestedReadingResponse,
    TelemetryReadingCreate,
    TelemetryReadingResponse,
)
from app.services import TelemetryService

router = APIRouter(prefix="/api/v1", tags=["Telemetry"])


@router.post(
    "/telemetry/readings",
    response_model=TelemetryIngestedReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_telemetry_reading(
    reading: TelemetryReadingCreate,
    db: Annotated[Session, Depends(get_db)],
) -> TelemetryIngestedReadingResponse:
    try:
        operation = TelemetryService(db).ingest_reading_operation(
            sensor_id=reading.sensor_id,
            value=reading.value,
            recorded_at=reading.recorded_at,
        )
    except AlertThresholdConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    from_thread.run(publish_committed_events, operation.events)

    return operation.result


@router.get(
    "/machines/{machine_id}/telemetry",
    response_model=list[TelemetryReadingResponse],
)
def get_machine_telemetry(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[TelemetryReadingResponse]:
    return TelemetryService(db).get_machine_telemetry(machine_id)
