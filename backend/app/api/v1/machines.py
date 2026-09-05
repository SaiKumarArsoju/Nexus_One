from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.domain.alert_rules import AlertThresholdConfigurationError
from app.domain.health_scoring import HealthScoringDataError
from app.domain.predictive_features import (
    PredictiveFeatureConfigurationError,
    PredictiveFeatureDataError,
    PredictiveFeatureWindow,
)
from app.schemas import (
    MachineDetailResponse,
    MachineFleetItemResponse,
    MachineHealthScoreResponse,
    MachinePredictiveFeaturesResponse,
    MachineTrendsResponse,
)
from app.services import HealthScoringService, MachineService, PredictiveFeatureService

router = APIRouter(prefix="/api/v1", tags=["Machines"])


@router.get(
    "/machines/{machine_id}/health-score",
    response_model=MachineHealthScoreResponse,
)
def get_machine_health_score(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    window: Annotated[
        PredictiveFeatureWindow,
        Query(description="Controlled lookback window"),
    ] = PredictiveFeatureWindow.TWENTY_FOUR_HOURS,
    end: Annotated[
        AwareDatetime | None,
        Query(description="Exclusive timezone-aware scoring-window end"),
    ] = None,
) -> MachineHealthScoreResponse:
    try:
        return HealthScoringService(db).get_machine_health_score(
            machine_id=machine_id,
            window=window,
            end=end,
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
    except (
        AlertThresholdConfigurationError,
        PredictiveFeatureConfigurationError,
        PredictiveFeatureDataError,
        HealthScoringDataError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/machines/{machine_id}/predictive-features",
    response_model=MachinePredictiveFeaturesResponse,
)
def get_machine_predictive_features(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    window: Annotated[
        PredictiveFeatureWindow,
        Query(description="Controlled lookback window"),
    ] = PredictiveFeatureWindow.TWENTY_FOUR_HOURS,
    end: Annotated[
        AwareDatetime | None,
        Query(description="Exclusive timezone-aware feature-window end"),
    ] = None,
) -> MachinePredictiveFeaturesResponse:
    try:
        return PredictiveFeatureService(db).get_machine_features(
            machine_id=machine_id,
            window=window,
            end=end,
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
    except (AlertThresholdConfigurationError, PredictiveFeatureConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


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


@router.get(
    "/machines/{machine_id}/trends",
    response_model=MachineTrendsResponse,
)
def get_machine_trends(
    machine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MachineTrendsResponse:
    trends = MachineService(db).get_machine_trends(machine_id)

    if trends is None:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    return trends
