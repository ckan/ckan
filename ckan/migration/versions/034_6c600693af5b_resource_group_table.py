# encoding: utf-8
"""034 Resource group table

Revision ID: 6c600693af5b
Revises: 6da92ef2df15
Create Date: 2018-09-04 18:49:00.683101

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '6c600693af5b'
down_revision = '6da92ef2df15'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'resource_group',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('package_id', sa.UnicodeText, sa.ForeignKey('package.id')),
        sa.Column('label', sa.UnicodeText),
        sa.Column('sort_order', sa.UnicodeText),
        sa.Column('extras', sa.UnicodeText),
        sa.Column('state', sa.UnicodeText),
        sa.Column('revision_id', sa.UnicodeText, sa.ForeignKey('revision.id')),
    )

    op.create_table(
        'resource_group_revision',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('package_id', sa.UnicodeText, sa.ForeignKey('package.id')),
        sa.Column('label', sa.UnicodeText),
        sa.Column('sort_order', sa.UnicodeText),
        sa.Column('extras', sa.UnicodeText),
        sa.Column('state', sa.UnicodeText),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.UnicodeText,
            sa.ForeignKey('resource_group.id')
        )
    )
    op.alter_column(
        'package_resource', 'package_id', new_column_name='resource_group_id'
    )
    op.alter_column(
        'package_resource_revision',
        'package_id',
        new_column_name='resource_group_id'
    )

    op.rename_table('package_resource', 'resource')
    op.rename_table('package_resource_revision', 'resource_revision')
    op.execute('ALTER INDEX package_resource_pkey RENAME TO resource_pkey')
    op.execute(
        'ALTER INDEX package_resource_revision_pkey '
        'RENAME TO resource_revision_pkey'
    )

    op.drop_constraint(
        'package_resource_revision_continuity_id_fkey', 'resource_revision'
    )
    op.drop_constraint(
        'package_resource_revision_package_id_fkey', 'resource_revision'
    )
    op.drop_constraint(
        'package_resource_revision_revision_id_fkey', 'resource_revision'
    )
    op.drop_constraint('package_resource_revision_id_fkey', 'resource')
    op.drop_constraint('package_resource_package_id_fkey', 'resource')

    op.create_foreign_key(
        'resource_resource_group_id_fkey', 'resource', 'resource_group',
        ['resource_group_id'], ['id']
    )
    op.create_foreign_key(
        'resource_revision_id_fkey', 'resource', 'revision', ['revision_id'],
        ['id']
    )
    op.create_foreign_key(
        'resource_revision_continuity_id_fkey', 'resource_revision',
        'resource', ['continuity_id'], ['id']
    )
    op.create_foreign_key(
        'resource_revision_resource_group_id_fkey', 'resource_revision',
        'resource_group', ['resource_group_id'], ['id']
    )
    op.create_foreign_key(
        'resource_revision_revision_id_fkey', 'resource_revision', 'revision',
        ['revision_id'], ['id']
    )


def downgrade():
    op.drop_constraint('resource_resource_group_id_fkey', 'resource')
    op.drop_constraint('resource_revision_id_fkey', 'resource')
    op.drop_constraint(
        'resource_revision_continuity_id_fkey', 'resource_revision'
    )
    op.drop_constraint(
        'resource_revision_resource_group_id_fkey', 'resource_revision'
    )
    op.drop_constraint(
        'resource_revision_revision_id_fkey', 'resource_revision'
    )

    op.rename_table('resource_revision', 'package_resource_revision')
    op.rename_table('resource', 'package_resource')
    op.execute('ALTER INDEX resource_pkey RENAME TO package_resource_pkey')
    op.execute(
        'ALTER INDEX resource_revision_pkey '
        'RENAME TO package_resource_revision_pkey'
    )

    op.alter_column(
        'package_resource_revision',
        'resource_group_id',
        new_column_name='package_id'
    )
    op.alter_column(
        'package_resource', 'resource_group_id', new_column_name='package_id'
    )

    op.create_foreign_key(
        'package_resource_package_id_fkey', 'package_resource', 'package',
        ['package_id'], ['id']
    )
    op.create_foreign_key(
        'package_resource_revision_id_fkey', 'package_resource', 'revision',
        ['revision_id'], ['id']
    )
    op.create_foreign_key(
        'package_resource_revision_revision_id_fkey',
        'package_resource_revision', 'revision', ['revision_id'], ['id']
    )
    op.create_foreign_key(
        'package_resource_revision_package_id_fkey',
        'package_resource_revision', 'package', ['package_id'], ['id']
    )
    op.create_foreign_key(
        'package_resource_revision_continuity_id_fkey',
        'package_resource_revision', 'package_resource', ['continuity_id'],
        ['id']
    )
    op.create_index(
        'idx_package_resource_pkg_id', 'package_resource', ['package_id']
    )
    op.create_index(
        'idx_package_resource_pkg_id_resource_id', 'package_resource',
        ['package_id', 'id']
    )

    op.drop_table('resource_group_revision')
    op.drop_table('resource_group')
