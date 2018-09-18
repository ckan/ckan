# encoding: utf-8
"""066 Default package type

Revision ID: ad16b3bd8cb6
Revises: 1fab0bc6439e
Create Date: 2018-09-04 18:49:11.624055

"""
from alembic import op
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'ad16b3bd8cb6'
down_revision = '1fab0bc6439e'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    pass


def downgrade():
    pass
