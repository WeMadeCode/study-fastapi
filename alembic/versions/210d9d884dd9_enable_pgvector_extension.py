"""enable pgvector extension

Revision ID: 210d9d884dd9
Revises: 7f2870eddaa5
Create Date: 2026-10-08 15:00:39.788911

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "210d9d884dd9"
down_revision: str | Sequence[str] | None = "7f2870eddaa5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS vector")
