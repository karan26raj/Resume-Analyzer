from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e7f9a3c6d2b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("embedding_chunks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id")), sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id")), sa.Column("document_type", sa.String(20), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("embedding", sa.JSON(), nullable=False), sa.Column("model", sa.String(100), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    for name, column in [("ix_embedding_chunks_id", "id"), ("ix_embedding_chunks_user_id", "user_id"), ("ix_embedding_chunks_resume_id", "resume_id"), ("ix_embedding_chunks_job_id", "job_id"), ("ix_embedding_chunks_document_type", "document_type")]:
        op.create_index(name, "embedding_chunks", [column])


def downgrade():
    op.drop_table("embedding_chunks")
