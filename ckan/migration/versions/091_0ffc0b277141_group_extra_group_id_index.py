# encoding: utf-8

"""group_extra group_id index

Revision ID: 0ffc0b277141
Revises: 980dcd44de4b
Create Date: 2019-09-11 12:16:42.792661

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = u'0ffc0b277141'
down_revision = u'980dcd44de4b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(u'idx_group_extra_group_id', u'group_extra', [u'group_id'])


def downgrade():
    op.drop_index(u'idx_group_extra_group_id')
