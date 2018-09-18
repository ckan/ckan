# encoding: utf-8
"""076 Rename view plugins 2

Revision ID: 59995aa965c0
Revises: 9cdc88c8896a
Create Date: 2018-09-04 18:49:15.123438

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '59995aa965c0'
down_revision = '9cdc88c8896a'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
