# encoding: utf-8
"""031 Move openid to new_field

Revision ID: 1b05245167d6
Revises: b16cbf164c8a
Create Date: 2018-09-04 18:48:59.666938

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '1b05245167d6'
down_revision = 'b16cbf164c8a'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
