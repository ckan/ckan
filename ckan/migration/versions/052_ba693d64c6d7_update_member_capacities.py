# encoding: utf-8
"""052 Update member capacities

Revision ID: ba693d64c6d7
Revises: a4fb0d85ced6
Create Date: 2018-09-04 18:49:06.885179

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'ba693d64c6d7'
down_revision = 'a4fb0d85ced6'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
