# encoding: utf-8
"""080 Continuity id indexes

Revision ID: 8224d872c64f
Revises: e0177a15d2c9
Create Date: 2018-09-04 18:49:16.546952

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '8224d872c64f'
down_revision = 'e0177a15d2c9'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_index(
        'idx_member_continuity_id', 'member_revision', ['continuity_id']
    )
    op.create_index(
        'idx_package_tag_continuity_id', 'package_tag_revision',
        ['continuity_id']
    )
    op.create_index(
        'idx_package_continuity_id', 'package_revision', ['continuity_id']
    )
    op.create_index(
        'idx_package_extra_continuity_id', 'package_extra_revision',
        ['continuity_id']
    )


def downgrade():
    op.drop_index('idx_member_continuity_id', 'member_revision')
    op.drop_index('idx_package_tag_continuity_id', 'package_tag_revision')
    op.drop_index('idx_package_continuity_id', 'package_revision')
    op.drop_index('idx_package_extra_continuity_id', 'package_extra_revision')
