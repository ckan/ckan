# encoding: utf-8
"""041 Resource new fields

Revision ID: 6817d4e3bdc3
Revises: 500a08f4818e
Create Date: 2018-09-04 18:49:03.042528

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '6817d4e3bdc3'
down_revision = '500a08f4818e'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    for table in ('resource', 'resource_revision'):
        op.add_column(table, sa.Column('name', sa.UnicodeText))
        op.add_column(table, sa.Column('resource_type', sa.UnicodeText))
        op.add_column(table, sa.Column('mimetype', sa.UnicodeText))
        op.add_column(table, sa.Column('mimetype_inner', sa.UnicodeText))
        op.add_column(table, sa.Column('size', sa.BigInteger))
        op.add_column(table, sa.Column('last_modified', sa.TIMESTAMP))
        op.add_column(table, sa.Column('cache_url', sa.UnicodeText))
        op.add_column(table, sa.Column('cache_last_updated', sa.TIMESTAMP))
        op.add_column(table, sa.Column('webstore_url', sa.UnicodeText))
        op.add_column(table, sa.Column('webstore_last_updated', sa.TIMESTAMP))


def downgrade():
    for table in ('resource', 'resource_revision'):
        op.drop_column(table, 'name')
        op.drop_column(table, 'resource_type')
        op.drop_column(table, 'mimetype')
        op.drop_column(table, 'mimetype_inner')
        op.drop_column(table, 'size')
        op.drop_column(table, 'last_modified')
        op.drop_column(table, 'cache_url')
        op.drop_column(table, 'cache_last_updated')
        op.drop_column(table, 'webstore_url')
        op.drop_column(table, 'webstore_last_updated')
