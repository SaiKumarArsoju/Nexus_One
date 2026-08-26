"""create alert thresholds table

Revision ID: b8b717ee8651
Revises: 42c28e6d4516
Create Date: 2026-08-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8b717ee8651"
down_revision: str | Sequence[str] | None = "42c28e6d4516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

sensor_type_enum = postgresql.ENUM(
    "TEMPERATURE",
    "PRESSURE",
    "VIBRATION",
    "RPM",
    "ENERGY",
    name="sensor_type",
    create_type=False,
)

alert_thresholds = sa.table(
    "alert_thresholds",
    sa.column("sensor_type", sensor_type_enum),
    sa.column("threshold_value", sa.Float()),
)


def upgrade() -> None:
    """Create and seed the global alert thresholds."""
    op.create_table(
        "alert_thresholds",
        sa.Column("sensor_type", sensor_type_enum, nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "threshold_value > 0",
            name="ck_alert_thresholds_threshold_value_positive",
        ),
        sa.PrimaryKeyConstraint("sensor_type"),
    )

    op.bulk_insert(
        alert_thresholds,
        [
            {"sensor_type": "TEMPERATURE", "threshold_value": 90.0},
            {"sensor_type": "PRESSURE", "threshold_value": 7.5},
            {"sensor_type": "VIBRATION", "threshold_value": 0.4},
            {"sensor_type": "RPM", "threshold_value": 2800.0},
            {"sensor_type": "ENERGY", "threshold_value": 28.0},
        ],
    )


def downgrade() -> None:
    """Remove only the alert thresholds table."""
    op.drop_table("alert_thresholds")
