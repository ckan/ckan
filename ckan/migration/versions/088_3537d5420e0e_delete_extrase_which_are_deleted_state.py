# encoding: utf-8
"""delete extrase which are deleted state

Revision ID: 3537d5420e0e
Revises: ff1b303cab77
Create Date: 2019-05-09 13:38:22.072361

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = u'3537d5420e0e'
down_revision = u'ff1b303cab77'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        u'package_extra_revision_continuity_id_fkey', u'package_extra_revision'
    )
    op.drop_constraint(
        u'group_extra_revision_continuity_id_fkey', u'group_extra_revision'
    )

    conn = op.get_bind()
    conn.execute(u'''DELETE FROM "package_extra" WHERE state='deleted';''')
    conn.execute(u'''DELETE FROM "group_extra" WHERE state='deleted';''')


def downgrade():
    op.create_foreign_key(
        u'package_extra_revision_continuity_id_fkey',
        u'package_extra_revision', u'package_extra', [u'continuity_id'],
        [u'id']
    )
    op.create_foreign_key(
        u'group_extra_revision_continuity_id_fkey', u'group_extra_revision',
        u'group_extra', [u'group_id'], [u'id']
    )
