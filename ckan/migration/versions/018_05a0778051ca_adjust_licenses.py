# encoding: utf-8
"""018 Adjust licenses

Revision ID: 05a0778051ca
Revises: 1250b2ff3e36
Create Date: 2018-09-04 18:48:54.288030

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '05a0778051ca'
down_revision = '1250b2ff3e36'
branch_labels = None
depends_on = None

tables = ['package', 'package_revision']


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    for table in tables:
        op.drop_column(table, 'license_id')
        op.add_column(table, sa.Column('license_id', sa.UnicodeText))
    op.drop_table('license')


def downgrade():

    op.create_table(
        'license',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Unicode(100)), sa.Column('state', sa.UnicodeText)
    )
    for table in tables:
        op.drop_column(table, 'license_id')
        op.add_column(
            table,
            sa.Column('license_id', sa.Integer, sa.ForeignKey('license.id'))
        )
