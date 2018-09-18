# encoding: utf-8
"""061 Add follower  group_table

Revision ID: 338d460bc460
Revises: 31ad11c518fc
Create Date: 2018-09-04 18:49:09.925977

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '338d460bc460'
down_revision = '31ad11c518fc'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'user_following_group',
        sa.Column('follower_id', sa.UnicodeText, nullable=False),
        sa.Column('object_id', sa.UnicodeText, nullable=False),
        sa.Column('datetime', sa.TIMESTAMP, nullable=False)
    )

    op.create_primary_key(
        'user_following_group_pkey', 'user_following_group',
        ['follower_id', 'object_id']
    )
    op.create_foreign_key(
        'user_following_group_user_id_fkey',
        'user_following_group',
        'user', ['follower_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'user_following_group_group_id_fkey',
        'user_following_group',
        'group', ['object_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )


def downgrade():
    op.drop_table('user_following_group')
