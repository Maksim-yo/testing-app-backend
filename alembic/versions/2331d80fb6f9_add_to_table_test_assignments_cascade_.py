"""Add to table test_assignments cascade deletion

Revision ID: 2331d80fb6f9
Revises: 5662f7ddfec5
Create Date: 2025-05-26 21:05:09.220590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2331d80fb6f9'
down_revision: Union[str, None] = '5662f7ddfec5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('test_assignments_test_id_fkey', 'test_assignments', type_='foreignkey')
    op.drop_constraint('test_assignments_employee_id_fkey', 'test_assignments', type_='foreignkey')
    op.create_foreign_key(None, 'test_assignments', 'tests', ['test_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'test_assignments', 'employees', ['employee_id'], ['id'], ondelete='CASCADE')
   
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###

    op.drop_constraint(None, 'test_assignments', type_='foreignkey')
    op.drop_constraint(None, 'test_assignments', type_='foreignkey')
    op.create_foreign_key('test_assignments_employee_id_fkey', 'test_assignments', 'employees', ['employee_id'], ['id'])
    op.create_foreign_key('test_assignments_test_id_fkey', 'test_assignments', 'tests', ['test_id'], ['id'])
    # ### end Alembic commands ###
