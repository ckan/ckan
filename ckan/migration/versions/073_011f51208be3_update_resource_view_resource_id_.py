# encoding: utf-8
"""073 Update resource view resource_id_constraint

Revision ID: 011f51208be3
Revises: 08dcb9233ad7
Create Date: 2018-09-04 18:49:14.072410

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '011f51208be3'
down_revision = '08dcb9233ad7'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_constraint('resource_view_resource_id_fkey', 'resource_view')
    op.create_foreign_key(
        'resource_view_resource_id_fkey',
        'resource_view',
        'resource', ['resource_id'], ['id'],
        ondelete='CASCADE',
        onupdate='CASCADE'
    )


def downgrade():
    op.drop_constraint('resource_view_resource_id_fkey', 'resource_view')
    op.create_foreign_key(
        'resource_view_resource_id_fkey', 'resource_view', 'resource',
        ['resource_id'], ['id']
    )
