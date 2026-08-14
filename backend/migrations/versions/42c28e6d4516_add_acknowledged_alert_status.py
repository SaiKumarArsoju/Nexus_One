"""add acknowledged alert status

Revision ID: 42c28e6d4516
Revises: c89d9c294217
Create Date: 2026-08-13 20:06:59.051966

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "42c28e6d4516"
down_revision: str | Sequence[str] | None = "c89d9c294217"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ACKNOWLEDGED to the alert_status PostgreSQL enum."""
    op.execute("ALTER TYPE alert_status ADD VALUE IF NOT EXISTS 'ACKNOWLEDGED'")


def downgrade() -> None:
    """Remove ACKNOWLEDGED from alert_status."""
    op.execute("""
        UPDATE alerts
        SET status = 'ACTIVE'
        WHERE status = 'ACKNOWLEDGED'
        """)

    op.execute("ALTER TYPE alert_status RENAME TO alert_status_old")

    op.execute("""
        CREATE TYPE alert_status AS ENUM (
            'ACTIVE',
            'RESOLVED'
        )
        """)

    op.execute("""
        ALTER TABLE alerts
        ALTER COLUMN status TYPE alert_status
        USING status::text::alert_status
        """)

    op.execute("DROP TYPE alert_status_old")
