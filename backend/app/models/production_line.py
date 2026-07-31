from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.factory import Factory
    from app.models.machine import Machine


class ProductionLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_lines"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    factory_id: Mapped[UUID] = mapped_column(
        ForeignKey("factories.id"),
        nullable=False,
    )

    factory: Mapped[Factory] = relationship(
        back_populates="production_lines",
    )

    machines: Mapped[list[Machine]] = relationship(
        back_populates="production_line",
        cascade="all, delete-orphan",
    )
