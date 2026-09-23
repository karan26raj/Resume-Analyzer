"""add structured analysis fields

Revision ID: e7f9a3c6d2b4
Revises: d4e6f8a2b5c1
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f9a3c6d2b4"
down_revision: Union[str, Sequence[str], None] = "d4e6f8a2b5c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analysis_results", sa.Column("weaknesses", sa.JSON(), nullable=True))
    op.add_column("analysis_results", sa.Column("recommendations", sa.JSON(), nullable=True))
    op.execute(
        "UPDATE analysis_results "
        "SET weaknesses = improvements, recommendations = improvements"
    )
    op.alter_column("analysis_results", "weaknesses", nullable=False)
    op.alter_column("analysis_results", "recommendations", nullable=False)
    op.drop_column("analysis_results", "improvements")


def downgrade() -> None:
    op.add_column("analysis_results", sa.Column("improvements", sa.JSON(), nullable=True))
    op.execute("UPDATE analysis_results SET improvements = recommendations")
    op.alter_column("analysis_results", "improvements", nullable=False)
    op.drop_column("analysis_results", "recommendations")
    op.drop_column("analysis_results", "weaknesses")
