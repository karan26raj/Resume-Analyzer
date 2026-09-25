from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cdf3df93ba88'
down_revision: Union[str, Sequence[str], None] = '894dc37b2dcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resumes', sa.Column('raw_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('resumes', 'raw_text')
