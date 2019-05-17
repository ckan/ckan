# encoding: utf-8
"""029 Version groups

Revision ID: 1bfdf4240915
Revises: cdd68fe9ba21
Create Date: 2018-09-04 18:48:59.007126

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '1bfdf4240915'
down_revision = 'cdd68fe9ba21'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'group_revision', sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('name', sa.UnicodeText, nullable=False),
        sa.Column('title', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
        sa.Column(
            'created', sa.DateTime, server_default=sa.func.current_timestamp()
        ), sa.Column('state', sa.UnicodeText),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column('continuity_id', sa.UnicodeText, sa.ForeignKey('group.id'))
    )

    op.create_table(
        'package_group_revision',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('package_id', sa.UnicodeText, sa.ForeignKey('package.id')),
        sa.Column('group_id', sa.UnicodeText, sa.ForeignKey('group.id')),
        sa.Column('state', sa.UnicodeText),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.UnicodeText, sa.ForeignKey('package_group.id')
        )
    )

    op.create_table(
        'group_extra_revision',
        sa.Column(
            'id',
            sa.UnicodeText,
            primary_key=True,
        ), sa.Column('group_id', sa.UnicodeText, sa.ForeignKey('group.id')),
        sa.Column('key', sa.UnicodeText), sa.Column('value', sa.UnicodeText),
        sa.Column('state', sa.UnicodeText),
        sa.Column(
            'revision_id',
            sa.UnicodeText,
            sa.ForeignKey('revision.id'),
            primary_key=True
        ),
        sa.Column(
            'continuity_id', sa.UnicodeText, sa.ForeignKey('group_extra.id')
        )
    )

    op.add_column('group', sa.Column('state', sa.UnicodeText))
    op.add_column('group', sa.Column('revision_id', sa.UnicodeText))
    op.create_foreign_key(
        'group_revision_id_fkey', 'group', 'revision', ['revision_id'], ['id']
    )

    op.add_column('package_group', sa.Column('state', sa.UnicodeText))
    op.add_column('package_group', sa.Column('revision_id', sa.UnicodeText))
    op.create_foreign_key(
        'package_group_revision_id_fkey', 'package_group', 'revision',
        ['revision_id'], ['id']
    )

    op.add_column('group_extra', sa.Column('state', sa.UnicodeText))
    op.add_column('group_extra', sa.Column('revision_id', sa.UnicodeText))
    op.create_foreign_key(
        'group_extra_revision_id_fkey', 'group_extra', 'revision',
        ['revision_id'], ['id']
    )


def downgrade():
    op.drop_column('group_extra', 'revision_id')
    op.drop_column('group_extra', 'state')

    op.drop_column('package_group', 'revision_id')
    op.drop_column('package_group', 'state')

    op.drop_column('group', 'revision_id')
    op.drop_column('group', 'state')

    op.drop_table('group_extra_revision')
    op.drop_table('package_group_revision')
    op.drop_table('group_revision')
