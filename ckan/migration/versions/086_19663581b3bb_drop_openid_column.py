# encoding: utf-8
"""086 Drop openid column

Revision ID: 19663581b3bb
Revises: f9bf3d5c4b4d
Create Date: 2018-09-04 18:49:18.650337

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '19663581b3bb'
down_revision = 'f9bf3d5c4b4d'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.drop_column('user', 'openid')


def downgrade():
    op.add_column('user', sa.Column('openid', sa.UnicodeText))
    op.create_index('idx_openid', 'user', ['openid'])
