# encoding: utf-8
"""048 Add activity streams tables

Revision ID: 4a7011172b3f
Revises: 883a7c406926
Create Date: 2018-09-04 18:49:05.463765

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '4a7011172b3f'
down_revision = '883a7c406926'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'activity',
        sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP),
        sa.Column('user_id', sa.UnicodeText),
        sa.Column('object_id', sa.UnicodeText),
        sa.Column('revision_id', sa.UnicodeText),
        sa.Column('activity_type', sa.UnicodeText),
        sa.Column('data', sa.UnicodeText),
    )

    op.create_table(
        'activity_detail',
        sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('activity_id', sa.UnicodeText, nullable=False),
        sa.Column('object_id', sa.UnicodeText),
        sa.Column('object_type', sa.UnicodeText),
        sa.Column('activity_type', sa.UnicodeText),
        sa.Column('data', sa.UnicodeText),
    )

    op.create_primary_key('activity_pkey', 'activity', ['id'])
    op.create_primary_key('activity_detail_pkey', 'activity_detail', ['id'])
    op.create_foreign_key(
        'activity_detail_activity_id_fkey', 'activity_detail', 'activity',
        ['activity_id'], ['id']
    )


def downgrade():
    op.drop_table('activity_detail')
    op.drop_table('activity')
