from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import SensorType
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.machine import Machine


class Sensor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sensors"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    sensor_type: Mapped[SensorType] = mapped_column(
        Enum(SensorType, name="sensor_type"),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    machine_id: Mapped[UUID] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    machine: Mapped[Machine] = relationship(
        back_populates="sensors",
    )
