from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.realtime import (
    CommittedOperation,
    PendingRealtimeEvent,
    telemetry_updated_event,
)
from app.repositories import TelemetryRepository
from app.schemas import (
    TelemetryIngestedReadingResponse,
    TelemetryReadingResponse,
)
from app.services.alert import AlertService

DEFAULT_TELEMETRY_HISTORY_LIMIT = 500
MAX_TELEMETRY_HISTORY_LIMIT = 5_000


class TelemetryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TelemetryRepository(db)
        self.alert_service = AlertService(db)

    def ingest_reading(
        self,
        sensor_id: UUID,
        value: float,
        recorded_at: datetime,
    ) -> TelemetryIngestedReadingResponse:
        return self.ingest_reading_operation(
            sensor_id=sensor_id,
            value=value,
            recorded_at=recorded_at,
        ).result

    def ingest_reading_operation(
        self,
        sensor_id: UUID,
        value: float,
        recorded_at: datetime,
    ) -> CommittedOperation[TelemetryIngestedReadingResponse]:
        sensor = self.repository.get_sensor(sensor_id)

        if sensor is None:
            raise HTTPException(
                status_code=404,
                detail="Sensor not found",
            )

        with self.db.begin_nested():
            reading = self.repository.create_reading(
                sensor_id=sensor_id,
                value=value,
                recorded_at=recorded_at,
            )
            alert_change = self.alert_service.evaluate_sensor_reading_change(
                machine_id=sensor.machine_id,
                sensor_type=sensor.sensor_type,
                value=value,
                commit=False,
            )

        self.db.commit()
        self.db.refresh(reading)

        events: list[PendingRealtimeEvent] = [
            telemetry_updated_event(
                sensor_id=str(sensor.id),
                machine_id=str(sensor.machine_id),
            )
        ]

        if alert_change is not None:
            events.append(alert_change.to_realtime_event())

        return CommittedOperation(
            result=TelemetryIngestedReadingResponse(
                id=reading.id,
                sensor_id=reading.sensor_id,
                value=reading.value,
                recorded_at=reading.recorded_at,
            ),
            events=tuple(events),
        )

    def get_machine_telemetry(
        self,
        machine_id: UUID,
    ) -> list[TelemetryReadingResponse]:
        machine = self.repository.get_machine(machine_id)

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Machine not found",
            )

        rows = self.repository.get_machine_telemetry(machine_id)

        return [
            TelemetryReadingResponse(
                sensor_id=row.sensor_id,
                sensor_name=row.name,
                sensor_type=row.sensor_type.value,
                unit=row.unit,
                value=row.value,
                recorded_at=row.recorded_at,
            )
            for row in rows
        ]

    def get_historical_readings(
        self,
        *,
        sensor_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = DEFAULT_TELEMETRY_HISTORY_LIMIT,
    ) -> list[TelemetryIngestedReadingResponse]:
        if self.repository.get_sensor(sensor_id) is None:
            raise LookupError("Sensor not found")

        start_utc = self._to_utc(start, parameter_name="start")
        end_utc = self._to_utc(end, parameter_name="end")

        if start_utc is not None and end_utc is not None and start_utc > end_utc:
            raise ValueError("start must be less than or equal to end")

        if not 1 <= limit <= MAX_TELEMETRY_HISTORY_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_TELEMETRY_HISTORY_LIMIT}")

        readings = self.repository.list_readings(
            sensor_id=sensor_id,
            start=start_utc,
            end=end_utc,
            limit=limit,
        )

        return [
            TelemetryIngestedReadingResponse(
                id=reading.id,
                sensor_id=reading.sensor_id,
                value=reading.value,
                recorded_at=reading.recorded_at,
            )
            for reading in readings
        ]

    @staticmethod
    def _to_utc(
        value: datetime | None,
        *,
        parameter_name: str,
    ) -> datetime | None:
        if value is None:
            return None

        if value.utcoffset() is None:
            raise ValueError(f"{parameter_name} must include a timezone")

        return value.astimezone(UTC)
