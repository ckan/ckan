# encoding: utf-8
"""044 Add task status

Revision ID: 4190eeeb8d73
Revises: bd38cd6502b2
Create Date: 2018-09-04 18:49:04.084036

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '4190eeeb8d73'
down_revision = 'bd38cd6502b2'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'task_status', sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('entity_id', sa.UnicodeText, nullable=False),
        sa.Column('entity_type', sa.UnicodeText, nullable=False),
        sa.Column('task_type', sa.UnicodeText, nullable=False),
        sa.Column('key', sa.UnicodeText, nullable=False),
        sa.Column('value', sa.UnicodeText, nullable=False),
        sa.Column('state', sa.UnicodeText), sa.Column('error', sa.UnicodeText),
        sa.Column('last_updated', sa.TIMESTAMP)
    )
    op.create_primary_key('task_status_pkey', 'task_status', ['id'])
    op.create_unique_constraint(
        'task_status_entity_id_task_type_key_key', 'task_status',
        ['entity_id', 'task_type', 'key']
    )


def downgrade():
    op.drop_constraint('task_status_pkey', 'task_status')
    op.drop_constraint(
        'task_status_entity_id_task_type_key_key', 'task_status'
    )
    op.drop_table('task_status')
