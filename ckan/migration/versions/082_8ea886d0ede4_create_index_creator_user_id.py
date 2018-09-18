# encoding: utf-8
"""082 Create index creator user_id

Revision ID: 8ea886d0ede4
Revises: a64cf4a79182
Create Date: 2018-09-04 18:49:17.265729

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '8ea886d0ede4'
down_revision = 'a64cf4a79182'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_index(
        'idx_package_creator_user_id', 'package', ['creator_user_id']
    )


def downgrade():
    op.drop_index('idx_package_creator_user_id', 'package')
