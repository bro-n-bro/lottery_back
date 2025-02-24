"""Add github link to lottery 

Revision ID: c74b0804179e
Revises: 278947729ab2
Create Date: 2025-02-23 18:16:01.064189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c74b0804179e'
down_revision: Union[str, None] = '278947729ab2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lotteries', sa.Column('github_link', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('lotteries', 'github_link')
    # ### end Alembic commands ###
