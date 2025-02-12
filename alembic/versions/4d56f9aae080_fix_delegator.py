"""Fix Delegator

Revision ID: 4d56f9aae080
Revises: 0c9e108cc36c
Create Date: 2025-02-13 00:04:23.723598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d56f9aae080'
down_revision: Union[str, None] = '0c9e108cc36c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('delegators_address_key', 'delegators', type_='unique')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('delegators_address_key', 'delegators', ['address'])
    # ### end Alembic commands ###
