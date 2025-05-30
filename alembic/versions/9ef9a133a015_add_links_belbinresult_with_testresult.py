"""Add links belbinresult with testresult

Revision ID: 9ef9a133a015
Revises: 08533563f0df
Create Date: 2025-05-20 10:51:11.083816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ef9a133a015'
down_revision: Union[str, None] = '08533563f0df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('belbin_results', sa.Column('test_result_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'belbin_results', 'test_results', ['test_result_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'belbin_results', type_='foreignkey')
    op.drop_column('belbin_results', 'test_result_id')
    # ### end Alembic commands ###
