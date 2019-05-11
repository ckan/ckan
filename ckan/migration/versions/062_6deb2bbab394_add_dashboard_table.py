# encoding: utf-8
"""062 Add dashboard table

Revision ID: 6deb2bbab394
Revises: 338d460bc460
Create Date: 2018-09-04 18:49:10.266290

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '6deb2bbab394'
down_revision = '338d460bc460'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'dashboard', sa.Column('user_id', sa.UnicodeText, nullable=False),
        sa.Column('activity_stream_last_viewed', sa.TIMESTAMP, nullable=False)
    )
    op.create_primary_key('dashboard_pkey', 'dashboard', ['user_id'])
    op.create_foreign_key(
        'dashboard_user_id_fkey',
        'dashboard',
        'user', ['user_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )


def downgrade():
    op.drop_table('dashboard')
