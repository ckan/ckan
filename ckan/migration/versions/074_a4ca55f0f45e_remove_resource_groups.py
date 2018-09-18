# encoding: utf-8
"""074 Remove resource groups

Revision ID: a4ca55f0f45e
Revises: 011f51208be3
Create Date: 2018-09-04 18:49:14.423978

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'a4ca55f0f45e'
down_revision = '011f51208be3'
branch_labels = None
depends_on = None

resource_indexes = ((
    'resource_revision', ((
        'idx_resource_period_resource_group',
        ('revision_timestamp', 'expired_timestamp', 'resource_group_id')
    ), )
), (
    'resource_group_revision', (
        (
            'idx_resource_group_period',
            ('revision_timestamp', 'expired_timestamp', 'id')
        ),
        (
            'idx_resource_group_period_package',
            ('revision_timestamp', 'expired_timestamp', 'package_id')
        ),
        ('idx_resource_group_current', ('current', )),
    )
))


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column(
        'resource',
        sa.Column(
            'package_id', sa.UnicodeText, nullable=False, server_default=''
        )
    )
    op.drop_column('resource', 'resource_group_id')
    op.add_column(
        'resource_revision',
        sa.Column(
            'package_id', sa.UnicodeText, nullable=False, server_default=''
        )
    )
    op.drop_column('resource_revision', 'resource_group_id')

    op.drop_table('resource_group_revision')
    op.drop_table('resource_group')


def downgrade():
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
        ), sa.Column('expired_id', sa.UnicodeText),
        sa.Column('revision_timestamp', sa.TIMESTAMP),
        sa.Column('expired_timestamp', sa.TIMESTAMP),
        sa.Column('current', sa.Boolean)
    )

    op.drop_column('resource', 'package_id')
    op.drop_column('resource_revision', 'package_id')

    op.add_column(
        'resource',
        sa.Column(
            'resource_group_id',
            sa.UnicodeText,
            nullable=False,
            server_default=''
        )
    )
    op.add_column(
        'resource_revision',
        sa.Column(
            'resource_group_id',
            sa.UnicodeText,
            nullable=False,
            server_default=''
        )
    )
    op.create_index(
        'idx_resource_resource_group_id', 'resource_revision',
        ['resource_group_id', 'current']
    )

    for table, indexes in resource_indexes:
        for index, fields in indexes:
            op.create_index(index, table, fields)
    op.create_foreign_key(
        'resource_resource_group_id_fkey', 'resource', 'resource_group',
        ['resource_group_id'], ['id']
    )
    op.create_foreign_key(
        'resource_revision_resource_group_id_fkey', 'resource_revision',
        'resource_group', ['resource_group_id'], ['id']
    )
