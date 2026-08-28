from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
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
    return TelemetryService(db).ingest_reading(
        sensor_id=reading.sensor_id,
        value=reading.value,
        recorded_at=reading.recorded_at,
    )


@router.get(
    "/machines/{machine_id}/telemetry",
    response_model=list[TelemetryReadingResponse],
)
def get_machine_telemetry(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[TelemetryReadingResponse]:
    return TelemetryService(db).get_machine_telemetry(machine_id)
