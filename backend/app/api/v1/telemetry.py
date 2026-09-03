from typing import Annotated
from uuid import UUID

from anyio import from_thread
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.domain.alert_rules import AlertThresholdConfigurationError
from app.realtime import publish_committed_events
from app.schemas import (
    TelemetryAggregateBucketResponse,
    TelemetryAggregationBucket,
    TelemetryIngestedReadingResponse,
    TelemetryReadingCreate,
    TelemetryReadingResponse,
)
from app.services import TelemetryService
from app.services.telemetry import (
    DEFAULT_TELEMETRY_HISTORY_LIMIT,
    MAX_TELEMETRY_HISTORY_LIMIT,
)

router = APIRouter(prefix="/api/v1", tags=["Telemetry"])


@router.get(
    "/telemetry/aggregate",
    response_model=list[TelemetryAggregateBucketResponse],
)
def get_aggregated_telemetry_readings(
    sensor_id: Annotated[
        UUID,
        Query(description="Sensor whose readings should be aggregated"),
    ],
    start: Annotated[
        AwareDatetime,
        Query(description="Inclusive timezone-aware start timestamp"),
    ],
    end: Annotated[
        AwareDatetime,
        Query(description="Exclusive timezone-aware end timestamp"),
    ],
    bucket: Annotated[
        TelemetryAggregationBucket,
        Query(description="Absolute UTC time-bucket size"),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> list[TelemetryAggregateBucketResponse]:
    try:
        return TelemetryService(db).get_aggregated_readings(
            sensor_id=sensor_id,
            start=start,
            end=end,
            bucket=bucket,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get(
    "/telemetry/readings",
    response_model=list[TelemetryIngestedReadingResponse],
)
def get_historical_telemetry_readings(
    sensor_id: Annotated[
        UUID,
        Query(description="Sensor whose readings should be returned"),
    ],
    db: Annotated[Session, Depends(get_db)],
    start: Annotated[
        AwareDatetime | None,
        Query(description="Inclusive timezone-aware start timestamp"),
    ] = None,
    end: Annotated[
        AwareDatetime | None,
        Query(description="Inclusive timezone-aware end timestamp"),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_TELEMETRY_HISTORY_LIMIT,
            description=(
                "Maximum recent readings to select before returning them oldest to newest"
            ),
        ),
    ] = DEFAULT_TELEMETRY_HISTORY_LIMIT,
) -> list[TelemetryIngestedReadingResponse]:
    try:
        return TelemetryService(db).get_historical_readings(
            sensor_id=sensor_id,
            start=start,
            end=end,
            limit=limit,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


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
