from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories import TelemetryRepository
from app.schemas import TelemetryReadingResponse


class TelemetryService:
    def __init__(self, db: Session) -> None:
        self.repository = TelemetryRepository(db)

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
