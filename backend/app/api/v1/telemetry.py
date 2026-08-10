from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import TelemetryReadingResponse
from app.services import TelemetryService

router = APIRouter(prefix="/api/v1", tags=["Telemetry"])


@router.get(
    "/machines/{machine_id}/telemetry",
    response_model=list[TelemetryReadingResponse],
)
def get_machine_telemetry(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[TelemetryReadingResponse]:
    return TelemetryService(db).get_machine_telemetry(machine_id)
