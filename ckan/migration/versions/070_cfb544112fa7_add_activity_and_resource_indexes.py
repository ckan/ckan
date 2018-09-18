# encoding: utf-8
"""070 Add activity and resource_indexes

Revision ID: cfb544112fa7
Revises: e7524c675cdb
Create Date: 2018-09-04 18:49:13.010411

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version

# revision identifiers, used by Alembic.
revision = 'cfb544112fa7'
down_revision = 'e7524c675cdb'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_index(
        'idx_activity_user_id', 'activity', ['user_id', 'timestamp']
    )
    op.create_index(
        'idx_activity_object_id', 'activity', ['object_id', 'timestamp']
    )
    op.create_index(
        'idx_activity_detail_activity_id', 'activity_detail', ['activity_id']
    )
    op.create_index(
        'idx_resource_resource_group_id', 'resource_revision',
        ['resource_group_id', 'current']
    )


def downgrade():
    op.drop_index('idx_activity_user_id', 'activity')
    op.drop_index('idx_activity_object_id', 'activity')
    op.drop_index('idx_activity_detail_activity_id', 'activity_detail')
    op.drop_index('idx_resource_resource_group_id', 'resource_revision')
