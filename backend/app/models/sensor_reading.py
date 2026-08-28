from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.sensor import Sensor


class SensorReading(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index(
            "ix_sensor_readings_sensor_id_recorded_at_id",
            "sensor_id",
            "recorded_at",
            "id",
        ),
    )

    sensor_id: Mapped[UUID] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"),
        nullable=False,
    )

    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    sensor: Mapped[Sensor] = relationship(
        back_populates="readings",
    )
