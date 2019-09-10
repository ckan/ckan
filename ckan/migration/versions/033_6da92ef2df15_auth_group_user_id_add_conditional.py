# encoding: utf-8
"""033 Auth group user id_add_conditional

Revision ID: 6da92ef2df15
Revises: d89e0731422d
Create Date: 2018-09-04 18:49:00.347621

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '6da92ef2df15'
down_revision = 'd89e0731422d'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.add_column('authorization_group_user', sa.Column('id', sa.UnicodeText))
    op.create_primary_key(
        'authorization_group_user_pkey', 'authorization_group_user', ['id']
    )


def downgrade():
    op.drop_column('authorization_group_user', 'id')
