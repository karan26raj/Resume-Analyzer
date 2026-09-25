from alembic import op
import sqlalchemy as sa

revision = "c5e8a1d3f7b9"
down_revision = "a7c3e9f1b2d4"
branch_labels = None
depends_on = None

COLUMNS = ("retrieved_evidence", "semantic_similarity", "score_breakdown", "requirements")


def upgrade():
    op.add_column("analysis_results", sa.Column("requirements", sa.JSON(), nullable=True))
    op.add_column("analysis_results", sa.Column("score_breakdown", sa.JSON(), nullable=True))
    op.add_column("analysis_results", sa.Column("semantic_similarity", sa.Float(), nullable=True))
    op.add_column("analysis_results", sa.Column("retrieved_evidence", sa.JSON(), nullable=True))


def downgrade():
    for column in COLUMNS:
        op.drop_column("analysis_results", column)
