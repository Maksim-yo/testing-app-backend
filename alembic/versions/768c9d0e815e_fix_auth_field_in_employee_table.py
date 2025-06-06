"""Fix auth field in employee table

Revision ID: 768c9d0e815e
Revises: df1e0896b460
Create Date: 2025-05-11 15:33:15.398272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '768c9d0e815e'
down_revision: Union[str, None] = 'df1e0896b460'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('employees', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.add_column('employees', sa.Column('clerk_id', sa.String(), nullable=True))
    op.drop_index('ix_employees_created_by', table_name='employees')
    op.create_index(op.f('ix_employees_clerk_id'), 'employees', ['clerk_id'], unique=True)
    op.create_foreign_key(None, 'employees', 'employees', ['created_by_id'], ['id'])
    op.drop_column('employees', 'created_by')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('employees', sa.Column('created_by', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'employees', type_='foreignkey')
    op.drop_index(op.f('ix_employees_clerk_id'), table_name='employees')
    op.create_index('ix_employees_created_by', 'employees', ['created_by'], unique=False)
    op.drop_column('employees', 'clerk_id')
    op.drop_column('employees', 'created_by_id')
    # ### end Alembic commands ###
