from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MachineStatus
from app.database.base import Base
from app.models.alert import Alert
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.production_line import ProductionLine
    from app.models.sensor import Sensor


class Machine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "machines"

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    model_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus, name="machine_status"),
        nullable=False,
        default=MachineStatus.OFFLINE,
    )

    installation_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    production_line_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    production_line: Mapped[ProductionLine] = relationship(
        back_populates="machines",
    )
    sensors: Mapped[list[Sensor]] = relationship(
        back_populates="machine",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="machine",
        cascade="all, delete-orphan",
    )
