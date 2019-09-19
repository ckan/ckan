# encoding: utf-8

"""resource package_id index

Revision ID: 01afcadbd8c0
Revises: 0ffc0b277141
Create Date: 2019-09-11 12:16:53.937813

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = u'01afcadbd8c0'
down_revision = u'0ffc0b277141'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(u'idx_package_resource_package_id', u'resource',
                    [u'package_id'])


def downgrade():
    op.drop_index(u'idx_package_resource_package_id')
