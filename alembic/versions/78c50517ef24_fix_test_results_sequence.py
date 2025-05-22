"""fix_test_results_sequence

Revision ID: 78c50517ef24
Revises: 994b43132f1f
Create Date: 2025-05-20 11:31:02.869907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78c50517ef24'
down_revision: Union[str, None] = '994b43132f1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade():
    op.execute("""
    SELECT setval('test_results_id_seq', (SELECT MAX(id) FROM test_results));
    """)

def downgrade():
    pass  # No need to undo this
