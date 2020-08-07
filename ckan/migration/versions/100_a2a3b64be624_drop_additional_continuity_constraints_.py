# -*- coding: utf-8 -*-
"""drop additional continuity constraints for multiple revisions

Revision ID: a2a3b64be624
Revises: 3ae4b17ed66d
Create Date: 2020-08-07 15:41:41.086364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = u"a2a3b64be624"
down_revision = u"3ae4b17ed66d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        u'group_revision_continuity_id_fkey', u'group_revision')

    op.drop_constraint(
        u'member_revision_group_id_fkey', u'member_revision')

    op.drop_constraint(
        u'package_tag_revision_continuity_id_fkey', u'package_tag_revision')

    op.drop_constraint(
        u'package_tag_revision_package_id_fkey', u'package_tag_revision')


def downgrade():
    op.create_foreign_key(
        u'group_revision_continuity_id_fkey', u'group_revision',
        u'group', [u'continuity_id'], [u'id']
    )

    op.create_foreign_key(
        u'member_revision_group_id_fkey', u'member_revision',
        u'group', [u'group_id'], [u'id']
    )

    op.create_foreign_key(
        u'package_tag_revision_continuity_id_fkey', u'package_tag_revision',
        u'package_tag', [u'continuity_id'], [u'id']
    )

    op.create_foreign_key(
        u'package_tag_revision_package_id_fkey', u'package_tag_revision',
        u'package', [u'package_id'], [u'id']
    )
    pass
