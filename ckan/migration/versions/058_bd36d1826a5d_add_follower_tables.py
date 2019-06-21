# encoding: utf-8
"""058 Add follower tables

Revision ID: bd36d1826a5d
Revises: 660a5aae527e
Create Date: 2018-09-04 18:49:08.908624

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'bd36d1826a5d'
down_revision = '660a5aae527e'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'user_following_dataset',
        sa.Column('follower_id', sa.UnicodeText, nullable=False),
        sa.Column('object_id', sa.UnicodeText, nullable=False),
        sa.Column('datetime', sa.TIMESTAMP, nullable=False)
    )
    op.create_table(
        'user_following_user',
        sa.Column('follower_id', sa.UnicodeText, nullable=False),
        sa.Column('object_id', sa.UnicodeText, nullable=False),
        sa.Column('datetime', sa.TIMESTAMP, nullable=False)
    )

    op.create_primary_key(
        'user_following_dataset_pkey', 'user_following_dataset',
        ['follower_id', 'object_id']
    )
    op.create_primary_key(
        'user_following_user_pkey', 'user_following_user',
        ['follower_id', 'object_id']
    )

    op.create_foreign_key(
        'user_following_dataset_follower_id_fkey',
        'user_following_dataset',
        'user', ['follower_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'user_following_dataset_object_id_fkey',
        'user_following_dataset',
        'package', ['object_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'user_following_user_follower_id_fkey',
        'user_following_user',
        'user', ['follower_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'user_following_user_object_id_fkey',
        'user_following_user',
        'user', ['object_id'], ['id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )


def downgrade():
    op.drop_table('user_following_dataset')
    op.drop_table('user_following_user')
