# encoding: utf-8
"""075 Rename view plugins

Revision ID: 9cdc88c8896a
Revises: a4ca55f0f45e
Create Date: 2018-09-04 18:49:14.766120

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '9cdc88c8896a'
down_revision = 'a4ca55f0f45e'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
