from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.health import MachineHealthResponse
from app.schemas.machine import (
    MachineDetailResponse,
    MachineFleetItemResponse,
    MachineTrendsResponse,
    TelemetryTrendPoint,
)
from app.schemas.telemetry import TelemetryReadingResponse

__all__ = [
    "MachineHealthResponse",
    "TelemetryReadingResponse",
    "DashboardSummaryResponse",
    "MachineFleetItemResponse",
    "MachineDetailResponse",
    "MachineTrendsResponse",
    "TelemetryTrendPoint",
]
