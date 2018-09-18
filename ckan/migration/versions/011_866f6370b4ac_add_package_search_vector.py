# encoding: utf-8
"""011 Add package search vector

Revision ID: 866f6370b4ac
Revises: 746205dde53d
Create Date: 2018-09-04 18:48:51.971937

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '866f6370b4ac'
down_revision = 'a6f13bf14d0c'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'package_search',
        sa.Column(
            'package_id',
            sa.Integer,
            sa.ForeignKey('package.id'),
            primary_key=True
        ), sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR)
    )


def downgrade():
    op.drop_table('package_search')
