# encoding: utf-8

"""delete extrase which are deleted state

Revision ID: 3537d5420e0e
Revises: ff1b303cab77
Create Date: 2019-05-09 13:38:22.072361

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '3537d5420e0e'
down_revision = 'ff1b303cab77'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        'package_extra_revision_continuity_id_fkey', 'package_extra_revision'
    )
    op.drop_constraint(
        'group_extra_revision_continuity_id_fkey', 'group_extra_revision'
    )

    conn = op.get_bind()
    conn.execute('''DELETE FROM "package_extra" WHERE state='deleted';''')
    conn.execute('''DELETE FROM "group_extra" WHERE state='deleted';''')


def downgrade():
    op.create_foreign_key(
        'package_extra_revision_continuity_id_fkey', 'package_extra_revision',
        'package_extra', ['continuity_id'], ['id']
    )
    op.create_foreign_key(
        'group_extra_revision_continuity_id_fkey', 'group_extra_revision',
        'group_extra', ['group_id'], ['id']
    )
