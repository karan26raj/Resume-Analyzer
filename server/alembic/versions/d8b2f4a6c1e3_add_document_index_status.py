from alembic import op
import sqlalchemy as sa

revision = "d8b2f4a6c1e3"
down_revision = "c5e8a1d3f7b9"
branch_labels = None
depends_on = None

TABLES = ("resumes", "jobs")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("index_status", sa.String(length=20), nullable=False, server_default="pending"))
        op.add_column(table, sa.Column("index_error", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("indexed_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("chunk_count", sa.Integer(), nullable=True))


def downgrade():
    for table in TABLES:
        for column in ("chunk_count", "indexed_at", "index_error", "index_status"):
            op.drop_column(table, column)
