from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import MachineDetailResponse, MachineFleetItemResponse
from app.services import MachineService

router = APIRouter(prefix="/api/v1", tags=["Machines"])


@router.get(
    "/machines",
    response_model=list[MachineFleetItemResponse],
)
def get_machine_fleet(
    db: Annotated[Session, Depends(get_db)],
) -> list[MachineFleetItemResponse]:
    return MachineService(db).get_fleet()


@router.get(
    "/machines/{machine_id}",
    response_model=MachineDetailResponse,
)
def get_machine_detail(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MachineDetailResponse:
    machine = MachineService(db).get_machine_detail(machine_id)

    if machine is None:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    return machine
