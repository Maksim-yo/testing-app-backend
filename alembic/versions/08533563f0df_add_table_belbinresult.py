"""Add table BelbinResult

Revision ID: 08533563f0df
Revises: 394330103862
Create Date: 2025-05-20 10:45:31.612136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08533563f0df'
down_revision: Union[str, None] = '394330103862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""

    # 1. Создаём таблицу belbin_results
    op.create_table(
        'belbin_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['belbin_roles.id']),
    )
    op.create_index(op.f('ix_belbin_results_id'), 'belbin_results', ['id'], unique=False)

    # 2. Добавляем колонку id во временном nullable виде
    op.add_column('test_results', sa.Column('id', sa.Integer(), nullable=True))

    # 3. Создаём последовательность
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS test_results_id_seq OWNED BY test_results.id;
        UPDATE test_results SET id = nextval('test_results_id_seq');
    """)

    # 4. Делаем колонку NOT NULL
    op.alter_column('test_results', 'id', nullable=False)

    # 5. Удаляем старый композитный первичный ключ
    op.drop_constraint('test_results_pkey', 'test_results', type_='primary')

    # 6. Создаём новый primary key по id
    op.create_primary_key('pk_test_results', 'test_results', ['id'])

    # 7. Добавляем дополнительные поля
    op.add_column('test_results', sa.Column('score', sa.Integer(), nullable=True))
    op.add_column('test_results', sa.Column('max_score', sa.Integer(), nullable=True))
    op.add_column('test_results', sa.Column('percent', sa.Float(), nullable=True))
    op.create_index(op.f('ix_test_results_id'), 'test_results', ['id'], unique=False)


    # ### end Alembic commands ###
def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_test_results_id'), table_name='test_results')
    op.drop_column('test_results', 'percent')
    op.drop_column('test_results', 'max_score')
    op.drop_column('test_results', 'score')

    op.drop_constraint('pk_test_results', 'test_results', type_='primary')
    op.drop_column('test_results', 'id')

    op.drop_index(op.f('ix_belbin_results_id'), table_name='belbin_results')
    op.drop_table('belbin_results')