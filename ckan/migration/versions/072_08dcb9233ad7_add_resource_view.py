# encoding: utf-8
"""072 Add resource view

Revision ID: 08dcb9233ad7
Revises: c16f081ef73a
Create Date: 2018-09-04 18:49:13.697490

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '08dcb9233ad7'
down_revision = 'c16f081ef73a'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'resource_view',
        sa.Column('id', sa.UnicodeText, nullable=False),
        sa.Column('resource_id', sa.UnicodeText),
        sa.Column('title', sa.UnicodeText),
        sa.Column('description', sa.UnicodeText),
        sa.Column('view_type', sa.UnicodeText, nullable=False),
        sa.Column('order', sa.Integer, nullable=False),
        sa.Column('config', sa.UnicodeText),
    )

    op.create_primary_key('resource_view_pkey', 'resource_view', ['id'])
    op.create_foreign_key(
        'resource_view_resource_id_fkey', 'resource_view', 'resource',
        ['resource_id'], ['id']
    )


def downgrade():
    op.drop_table('resource_view')
