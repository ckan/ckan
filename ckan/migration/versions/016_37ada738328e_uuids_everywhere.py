# encoding: utf-8
"""016 Uuids everywhere

Revision ID: 37ada738328e
Revises: 6d8ffebcaf54
Create Date: 2018-09-04 18:48:53.632517

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '37ada738328e'
down_revision = '6d8ffebcaf54'
branch_labels = None
depends_on = None

foreign_keys = [
    ('package_tag', 'package_id'),
    ('package_tag', 'tag_id'),
    ('package_extra', 'package_id'),
    ('package_resource', 'package_id'),
    ('package_tag_revision', 'package_id'),
    ('package_tag_revision', 'tag_id'),
    ('package_extra_revision', 'package_id'),
    ('package_resource_revision', 'package_id'),
    ('rating', 'package_id'),
    ('package_search', 'package_id'),
    ('package_role', 'package_id'),
    ('package_group', 'package_id'),
]
ids = [
    'package', 'package_tag', 'package_extra', 'package_resource',
    'package_revision', 'package_tag_revision', 'package_extra_revision',
    'package_resource_revision', 'tag'
]

continuity = [
    'package_revision', 'package_tag_revision', 'package_extra_revision',
    'package_resource_revision'
]

sequences = [
    'package_id_seq', 'package_extra_id_seq', 'package_resource_id_seq',
    'package_tag_id_seq', 'tag_id_seq'
]

combined_primary_keys = [
    'package_extra_revision', 'package_revision', 'package_tag_revision'
]


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    for table, column in foreign_keys:
        op.drop_column(table, column)
    for table in continuity:
        op.drop_column(table, 'continuity_id')
    for table in ids:
        op.alter_column(table, 'id', type_=sa.UnicodeText, server_default=None)

    for table, column in foreign_keys:
        op.add_column(
            table,
            sa.Column(
                column, sa.UnicodeText,
                sa.ForeignKey(column.replace('_', '.'))
            )
        )
    for table in continuity:
        op.add_column(
            table,
            sa.Column(
                'continuity_id', sa.UnicodeText,
                sa.ForeignKey(table.replace('_revision', '.id'))
            )
        )
    for table in combined_primary_keys:
        op.create_primary_key(table + '_pkey', table, ['id', 'revision_id'])

    op.execute(
        sa.schema.DropSequence(sa.schema.Sequence('package_extra_id_seq'))
    )
    op.execute(sa.schema.DropSequence(sa.schema.Sequence('package_id_seq')))
    op.execute(
        sa.schema.DropSequence(sa.schema.Sequence('package_tag_id_seq'))
    )
    op.execute(
        sa.schema.DropSequence(sa.schema.Sequence('package_resource_id_seq'))
    )
    op.execute(sa.schema.DropSequence(sa.schema.Sequence('tag_id_seq')))
    op.execute(sa.schema.DropSequence(sa.schema.Sequence('revision_id_seq')))


def downgrade():
    for table, column in foreign_keys:
        op.drop_column(table, column)
    for table in continuity:
        op.drop_column(table, 'continuity_id')

    for table in ids:
        op.drop_column(table, 'id')
        op.add_column(
            table,
            sa.Column(
                'id',
                sa.Integer,
                primary_key=True,
                autoincrement=True,
                nullable=False,
                unique=True
            )
        )

    for table, column in foreign_keys:
        op.add_column(
            table,
            sa.Column(
                column, sa.Integer, sa.ForeignKey(column.replace('_', '.'))
            )
        )
    for table in continuity:
        op.add_column(
            table,
            sa.Column(
                'continuity_id', sa.Integer,
                sa.ForeignKey(table.replace('_revision', '.id'))
            )
        )
