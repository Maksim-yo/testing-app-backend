"""Add unique field for email in employee table

Revision ID: 0f19cd31e7d0
Revises: 80229d100461
Create Date: 2025-05-22 12:23:55.431128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f19cd31e7d0'
down_revision: Union[str, None] = '80229d100461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'employees', ['email'])

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###

    op.drop_constraint(None, 'employees', type_='unique')
    # ### end Alembic commands ###
