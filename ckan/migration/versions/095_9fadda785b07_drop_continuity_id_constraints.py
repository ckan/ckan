# encoding: utf-8

"""drop continuity_id constraints

Revision ID: 9fadda785b07
Revises: 588d7cfb9a41
Create Date: 2020-04-26 22:27:35.761525

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = u'9fadda785b07'
down_revision = u'588d7cfb9a41'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        u'member_revision_continuity_id_fkey', u'member_revision')
    op.drop_constraint(
        u'resource_revision_continuity_id_fkey', u'resource_revision')
    op.drop_constraint(
        u'package_revision_continuity_id_fkey', u'package_revision')


def downgrade():
    op.create_foreign_key(
        u'member_revision_continuity_id_fkey', u'member_revision', u'member',
        [u'continuity_id'], [u'id']
    )
    op.create_foreign_key(
        u'resource_revision_continuity_id_fkey', u'resource_revision',
        u'resource', [u'continuity_id'], [u'id']
    )
    op.create_foreign_key(
        u'package_revision_continuity_id_fkey', u'package_revision',
        u'package', [u'continuity_id'], [u'id']
    )
