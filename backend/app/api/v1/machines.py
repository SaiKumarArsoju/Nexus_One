from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import MachineFleetItemResponse
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
