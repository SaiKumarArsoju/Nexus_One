from sqlalchemy import CheckConstraint, Float
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SensorType
from app.database.base import Base
from app.models.mixins import TimestampMixin


class AlertThreshold(TimestampMixin, Base):
    __tablename__ = "alert_thresholds"
    __table_args__ = (
        CheckConstraint(
            "threshold_value > 0",
            name="ck_alert_thresholds_threshold_value_positive",
        ),
    )

    sensor_type: Mapped[SensorType] = mapped_column(
        ENUM(SensorType, name="sensor_type", create_type=False),
        primary_key=True,
    )

    threshold_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
