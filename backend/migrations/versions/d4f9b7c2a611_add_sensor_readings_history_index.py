"""add sensor readings history index

Revision ID: d4f9b7c2a611
Revises: b8b717ee8651
Create Date: 2026-08-28 09:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f9b7c2a611"
down_revision: str | Sequence[str] | None = "b8b717ee8651"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add an ordered, sensor-scoped telemetry history index."""
    op.drop_index(
        "ix_sensor_readings_sensor_id",
        table_name="sensor_readings",
    )
    op.create_index(
        "ix_sensor_readings_sensor_id_recorded_at_id",
        "sensor_readings",
        ["sensor_id", "recorded_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Restore the original single-column sensor index."""
    op.drop_index(
        "ix_sensor_readings_sensor_id_recorded_at_id",
        table_name="sensor_readings",
    )
    op.create_index(
        "ix_sensor_readings_sensor_id",
        "sensor_readings",
        ["sensor_id"],
        unique=False,
    )
