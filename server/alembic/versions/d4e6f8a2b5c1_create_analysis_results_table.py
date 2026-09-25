from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e6f8a2b5c1"
down_revision: Union[str, Sequence[str], None] = "b2d9a037a1e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("improvements", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_results_id"), "analysis_results", ["id"], unique=False)
    op.create_index(op.f("ix_analysis_results_job_id"), "analysis_results", ["job_id"], unique=False)
    op.create_index(op.f("ix_analysis_results_resume_id"), "analysis_results", ["resume_id"], unique=False)
    op.create_index(op.f("ix_analysis_results_user_id"), "analysis_results", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_analysis_results_user_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_resume_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_job_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_id"), table_name="analysis_results")
    op.drop_table("analysis_results")
