# encoding: utf-8
"""077 Add revisions to system_info

Revision ID: 51171a04d86d
Revises: 59995aa965c0
Create Date: 2018-09-04 18:49:15.478074

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '51171a04d86d'
down_revision = '59995aa965c0'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column(
        'system_info',
        sa.Column(
            'state', sa.UnicodeText, nullable=False, server_default='active'
        )
    )
    op.add_column(
        'system_info_revision',
        sa.Column(
            'state', sa.UnicodeText, nullable=False, server_default='active'
        )
    )

    op.add_column(
        'system_info_revision', sa.Column('expired_id', sa.UnicodeText)
    )
    op.add_column(
        'system_info_revision', sa.Column('revision_timestamp', sa.TIMESTAMP)
    )
    op.add_column(
        'system_info_revision', sa.Column('expired_timestamp', sa.TIMESTAMP)
    )
    op.add_column('system_info_revision', sa.Column('current', sa.Boolean))

    op.drop_constraint('system_info_revision_key_key', 'system_info_revision')


def downgrade():
    op.create_unique_constraint(
        'system_info_revision_key_key', 'system_info_revision', ['key']
    )

    op.drop_column('system_info', 'state')
    op.drop_column('system_info_revision', 'state')

    op.drop_column('system_info_revision', 'expired_id')
    op.drop_column('system_info_revision', 'revision_timestamp')
    op.drop_column('system_info_revision', 'expired_timestamp')
    op.drop_column('system_info_revision', 'current')
