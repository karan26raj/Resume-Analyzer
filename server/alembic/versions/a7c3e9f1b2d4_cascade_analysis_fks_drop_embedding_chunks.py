"""cascade analysis foreign keys and drop embedding chunks

Deleting a resume or job now removes its analysis results. Vectors are
stored in Qdrant, so the unused embedding_chunks table is dropped.

Revision ID: a7c3e9f1b2d4
Revises: f1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa

revision = "a7c3e9f1b2d4"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def _replace_analysis_fk(column: str, referred_table: str, ondelete: str | None) -> None:
    name = f"analysis_results_{column}_fkey"
    op.drop_constraint(name, "analysis_results", type_="foreignkey")
    op.create_foreign_key(
        name,
        "analysis_results",
        referred_table,
        [column],
        ["id"],
        ondelete=ondelete,
    )


def upgrade():
    _replace_analysis_fk("resume_id", "resumes", "CASCADE")
    _replace_analysis_fk("job_id", "jobs", "CASCADE")
    op.drop_table("embedding_chunks")


def downgrade():
    op.create_table(
        "embedding_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id")),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id")),
        sa.Column("document_type", sa.String(20), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name, column in [
        ("ix_embedding_chunks_id", "id"),
        ("ix_embedding_chunks_user_id", "user_id"),
        ("ix_embedding_chunks_resume_id", "resume_id"),
        ("ix_embedding_chunks_job_id", "job_id"),
        ("ix_embedding_chunks_document_type", "document_type"),
    ]:
        op.create_index(name, "embedding_chunks", [column])

    _replace_analysis_fk("job_id", "jobs", None)
    _replace_analysis_fk("resume_id", "resumes", None)
