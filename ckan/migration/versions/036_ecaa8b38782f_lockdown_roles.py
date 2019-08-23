# encoding: utf-8
"""036 Lockdown roles

Revision ID: ecaa8b38782f
Revises: 81148ccebd6c
Create Date: 2018-09-04 18:49:01.359019

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'ecaa8b38782f'
down_revision = '81148ccebd6c'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
