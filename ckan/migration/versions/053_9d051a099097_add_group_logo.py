# encoding: utf-8
"""053 Add group logo

Revision ID: 9d051a099097
Revises: ba693d64c6d7
Create Date: 2018-09-04 18:49:07.217429

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '9d051a099097'
down_revision = 'ba693d64c6d7'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column('group', sa.Column('image_url', sa.UnicodeText))
    op.add_column('group_revision', sa.Column('image_url', sa.UnicodeText))


def downgrade():
    op.drop_column('group', 'image_url')
    op.drop_column('group_revision', 'image_url')
