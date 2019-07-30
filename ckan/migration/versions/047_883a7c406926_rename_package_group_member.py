# encoding: utf-8
"""047 Rename package_group_member

Revision ID: 883a7c406926
Revises: b69e9b80396f
Create Date: 2018-09-04 18:49:05.130215

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '883a7c406926'
down_revision = 'b69e9b80396f'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.rename_table('package_group', 'member')
    op.rename_table('package_group_revision', 'member_revision')

    op.alter_column(
        'member', 'package_id', new_column_name='table_id', nullable=False
    )
    op.alter_column(
        'member_revision',
        'package_id',
        new_column_name='table_id',
        nullable=False
    )

    op.drop_constraint('package_group_revision_pkey', 'member_revision')
    op.drop_constraint(
        'package_group_revision_continuity_id_fkey', 'member_revision'
    )
    op.drop_constraint(
        'package_group_revision_group_id_fkey', 'member_revision'
    )
    op.drop_constraint(
        'package_group_revision_package_id_fkey', 'member_revision'
    )
    op.drop_constraint(
        'package_group_revision_revision_id_fkey', 'member_revision'
    )

    op.drop_constraint('package_group_pkey', 'member')
    op.drop_constraint('package_group_group_id_fkey', 'member')
    op.drop_constraint('package_group_package_id_fkey', 'member')
    op.drop_constraint('package_group_revision_id_fkey', 'member')

    op.add_column(
        'member', sa.Column('table_name', sa.UnicodeText, nullable=False)
    )
    op.add_column(
        'member', sa.Column('capacity', sa.UnicodeText, nullable=False)
    )
    op.add_column(
        'member_revision',
        sa.Column('table_name', sa.UnicodeText, nullable=False)
    )
    op.add_column(
        'member_revision',
        sa.Column('capacity', sa.UnicodeText, nullable=False)
    )

    op.create_primary_key('member_pkey', 'member', ['id'])
    op.create_primary_key(
        'member_revision_pkey', 'member_revision', ['id', 'revision_id']
    )

    op.create_foreign_key(
        'member_group_id_fkey', 'member', 'group', ['group_id'], ['id']
    )
    op.create_foreign_key(
        'member_revision_id_fkey', 'member', 'revision', ['revision_id'],
        ['id']
    )
    op.create_foreign_key(
        'member_revision_continuity_id_fkey', 'member_revision', 'member',
        ['continuity_id'], ['id']
    )
    op.create_foreign_key(
        'member_revision_group_id_fkey', 'member_revision', 'group',
        ['group_id'], ['id']
    )
    op.create_foreign_key(
        'member_revision_revision_id_fkey', 'member_revision', 'revision',
        ['revision_id'], ['id']
    )

    op.add_column('group', sa.Column('type', sa.UnicodeText, nullable=False))
    op.add_column(
        'group_revision', sa.Column('type', sa.UnicodeText, nullable=False)
    )

    op.add_column('package', sa.Column('type', sa.UnicodeText))
    op.add_column('package_revision', sa.Column('type', sa.UnicodeText))


def downgrade():
    op.drop_column('package', 'type')
    op.drop_column('package_revision', 'type')

    op.drop_column('group', 'type')
    op.drop_column('group_revision', 'type')

    op.drop_constraint('member_revision_continuity_id_fkey', 'member_revision')
    op.drop_constraint('member_revision_group_id_fkey', 'member_revision')
    op.drop_constraint('member_revision_revision_id_fkey', 'member_revision')
    op.drop_constraint('member_group_id_fkey', 'member')
    op.drop_constraint('member_revision_id_fkey', 'member')

    op.drop_constraint('member_revision_pkey', 'member_revision')
    op.drop_constraint('member_pkey', 'member')

    op.drop_column('member_revision', 'table_name')
    op.drop_column('member_revision', 'capacity')

    op.drop_column('member', 'table_name')
    op.drop_column('member', 'capacity')

    op.alter_column(
        'member_revision',
        'table_id',
        new_column_name='package_id',
        nullable=True
    )
    op.alter_column(
        'member', 'table_id', new_column_name='package_id', nullable=True
    )

    op.create_primary_key('package_group_pkey', 'member', ['id'])
    op.create_primary_key(
        'package_group_revision_pkey', 'member_revision',
        ['id', 'revision_id']
    )

    op.create_foreign_key(
        'package_group_group_id_fkey', 'member', 'group', ['group_id'], ['id']
    )
    op.create_foreign_key(
        'package_group_package_id_fkey', 'member', 'package', ['package_id'],
        ['id']
    )
    op.create_foreign_key(
        'package_group_revision_id_fkey', 'member', 'revision',
        ['revision_id'], ['id']
    )

    op.create_foreign_key(
        'package_group_revision_continuity_id_fkey', 'member_revision',
        'member', ['continuity_id'], ['id']
    )
    op.create_foreign_key(
        'package_group_revision_group_id_fkey', 'member_revision', 'group',
        ['group_id'], ['id']
    )
    op.create_foreign_key(
        'package_group_revision_package_id_fkey', 'member_revision', 'package',
        ['package_id'], ['id']
    )
    op.create_foreign_key(
        'package_group_revision_revision_id_fkey', 'member_revision',
        'revision', ['revision_id'], ['id']
    )

    op.rename_table('member_revision', 'package_group_revision')
    op.rename_table('member', 'package_group')
