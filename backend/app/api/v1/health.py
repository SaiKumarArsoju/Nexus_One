from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import MachineHealthResponse
from app.services import MachineHealthService

router = APIRouter(prefix="/api/v1", tags=["Machine Health"])


@router.get(
    "/machines/{machine_id}/health",
    response_model=MachineHealthResponse,
)
def get_machine_health(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MachineHealthResponse:
    return MachineHealthService(db).get_health(machine_id)
