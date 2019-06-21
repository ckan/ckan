# encoding: utf-8
"""015 Remove state_object

Revision ID: 6d8ffebcaf54
Revises: 93519b684820
Create Date: 2018-09-04 18:48:53.302758

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '6d8ffebcaf54'
down_revision = '93519b684820'
branch_labels = None
depends_on = None

stateful_tables = [
    'license', 'package', 'package_revision', 'package_tag',
    'package_tag_revision', 'package_extra', 'package_extra_revision',
    'package_resource', 'package_resource_revision', 'revision'
]


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    for table_name in stateful_tables:
        op.add_column(table_name, sa.Column('state', sa.UnicodeText))
        op.drop_column(table_name, 'state_id')

    op.drop_table('state')


def downgrade():
    op.create_table(
        'state',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100)),
    )

    for table_name in stateful_tables:
        op.drop_column(table_name, 'state')
        op.add_column(table_name, sa.Column('state_id', sa.Integer))
