# encoding: utf-8
"""039 Add expired id and_dates

Revision ID: cca459c76d45
Revises: fd6622e3d964
Create Date: 2018-09-04 18:49:02.364964

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'cca459c76d45'
down_revision = 'fd6622e3d964'
branch_labels = None
depends_on = None

tables = [
    'package_revision', 'package_extra_revision', 'group_revision',
    'group_extra_revision', 'package_group_revision', 'package_tag_revision',
    'resource_group_revision', 'resource_revision',
    'package_relationship_revision'
]
indexes = (
    (
        'package_revision', (
            (
                'idx_package_period',
                ('revision_timestamp', 'expired_timestamp', 'id')
            ),
            ('idx_package_current', ('current', )),
        )
    ),
    (
        'package_extra_revision', (
            (
                'idx_package_extra_period',
                ('revision_timestamp', 'expired_timestamp', 'id')
            ),
            (
                'idx_package_extra_period_package',
                ('revision_timestamp', 'expired_timestamp', 'package_id')
            ),
            ('idx_package_extra_current', ('current', )),
        )
    ),
    (
        'package_group_revision', (
            (
                'idx_package_group_period_package_group', (
                    'revision_timestamp', 'expired_timestamp', 'package_id',
                    'group_id'
                )
            ),
            ('idx_package_group_current', ('current', )),
        )
    ),
    (
        'package_tag_revision', (
            (
                'idx_period_package_tag', (
                    'revision_timestamp', 'expired_timestamp', 'package_id',
                    'tag_id'
                )
            ),
            ('idx_package_tag_current', ('current', )),
        )
    ),
    (
        'package_relationship_revision', (
            (
                'idx_period_package_relationship', (
                    'revision_timestamp', 'expired_timestamp',
                    'object_package_id', 'subject_package_id'
                )
            ),
            ('idx_package_relationship_current', ('current', )),
        )
    ),
    (
        'resource_revision', (
            (
                'idx_resource_period',
                ('revision_timestamp', 'expired_timestamp', 'id')
            ),
            (
                'idx_resource_period_resource_group', (
                    'revision_timestamp', 'expired_timestamp',
                    'resource_group_id'
                )
            ),
            ('idx_resource_current', ('current', )),
        )
    ),
    (
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
    ),
    (
        'group_revision', (
            (
                'idx_group_period',
                ('revision_timestamp', 'expired_timestamp', 'id')
            ),
            ('idx_group_current', ('current', )),
        )
    ),
    (
        'group_extra_revision', (
            (
                'idx_group_extra_period',
                ('revision_timestamp', 'expired_timestamp', 'id')
            ),
            (
                'idx_group_extra_period_group',
                ('revision_timestamp', 'expired_timestamp', 'group_id')
            ),
            ('idx_group_extra_current', ('current', )),
        )
    ),
)


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return

    for table in tables:
        op.add_column(table, sa.Column('expired_id', sa.UnicodeText))
        op.add_column(table, sa.Column('revision_timestamp', sa.TIMESTAMP))
        op.add_column(table, sa.Column('expired_timestamp', sa.TIMESTAMP))
        op.add_column(table, sa.Column('current', sa.Boolean))
    op.add_column('revision', sa.Column('approved_timestamp', sa.TIMESTAMP))

    for table, items in indexes:
        for index, columns in items:
            op.create_index(index, table, list(columns))


def downgrade():
    for table, items in reversed(indexes):
        for index, _ in items:
            op.drop_index(index, table)

    op.drop_column('revision', 'approved_timestamp')
    for table in reversed(tables):
        op.drop_column(table, 'expired_id')
        op.drop_column(table, 'revision_timestamp')
        op.drop_column(table, 'expired_timestamp')
        op.drop_column(table, 'current')
