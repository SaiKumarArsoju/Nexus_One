from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories import TelemetryRepository
from app.schemas import (
    TelemetryIngestedReadingResponse,
    TelemetryReadingResponse,
)


class TelemetryService:
    def __init__(self, db: Session) -> None:
        self.repository = TelemetryRepository(db)

    def ingest_reading(
        self,
        sensor_id: UUID,
        value: float,
        recorded_at: datetime,
    ) -> TelemetryIngestedReadingResponse:
        sensor = self.repository.get_sensor(sensor_id)

        if sensor is None:
            raise HTTPException(
                status_code=404,
                detail="Sensor not found",
            )

        reading = self.repository.create_reading(
            sensor_id=sensor_id,
            value=value,
            recorded_at=recorded_at,
        )

        return TelemetryIngestedReadingResponse(
            id=reading.id,
            sensor_id=reading.sensor_id,
            value=reading.value,
            recorded_at=reading.recorded_at,
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
