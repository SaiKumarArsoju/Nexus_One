from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field


class TelemetryReadingCreate(BaseModel):
    sensor_id: UUID
    value: float = Field(allow_inf_nan=False)
    recorded_at: AwareDatetime


class TelemetryIngestedReadingResponse(BaseModel):
    id: UUID
    sensor_id: UUID
    value: float
    recorded_at: datetime


class TelemetryReadingResponse(BaseModel):
    sensor_id: UUID
    sensor_name: str
    sensor_type: str
    unit: str
    value: float
    recorded_at: datetime


class TelemetryAggregationBucket(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"


class TelemetryAggregateBucketResponse(BaseModel):
    bucket_start: datetime
    average: float
    minimum: float
    maximum: float
    count: int
